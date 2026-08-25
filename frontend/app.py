import streamlit as st
import requests
import base64
import time
from io import BytesIO
from PIL import Image

import os
from dotenv import load_dotenv
load_dotenv()

st.set_page_config(page_title="OCR Pipeline Dashboard", layout="wide")

st.title("📄 OCR Distributed Pipeline")
st.markdown("Upload an image or PDF to extract text using our distributed Celery+Redis backend.")

# FastAPI endpoint URL
API_URL = os.getenv("API_URL", "http://localhost:8000/ocr")

# Initialize session state variables
if "task_id" not in st.session_state:
    st.session_state.task_id = None
if "results" not in st.session_state:
    st.session_state.results = None
if "is_cached" not in st.session_state:
    st.session_state.is_cached = False
if "processing_time" not in st.session_state:
    st.session_state.processing_time = None
if "evaluation_metrics" not in st.session_state:
    st.session_state.evaluation_metrics = None
if "retrieve_time" not in st.session_state:
    st.session_state.retrieve_time = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

uploaded_file = st.file_uploader("Choose a file (PDF, PNG, JPG, JPEG, WEBP)", type=["pdf", "png", "jpg", "jpeg", "webp"])

testing_phase = False

if uploaded_file is not None:
    st.info(f"File uploaded: {uploaded_file.name}")
    
    testing_phase = st.toggle("Enable Testing Phase")
    ground_truth_text = ""
    if testing_phase:
        ground_truth_text = st.text_area("Paste Ground Truth Text here for Evaluation (Optional)", height=150)
    
    if st.button("Run OCR Pipeline", type="primary"):
        # Reset state for new run
        st.session_state.task_id = None
        st.session_state.results = None
        st.session_state.chat_history = []
        
        # 1. Submit the file and get a task ID
        with st.spinner("Submitting document to the queue..."):
            try:
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                data = {}
                if testing_phase and ground_truth_text.strip():
                    data["ground_truth"] = ground_truth_text.strip()
                
                response = requests.post(API_URL, files=files, data=data)
                
                if response.status_code == 200:
                    resp_data = response.json()
                    st.session_state.task_id = resp_data.get("task_id")
                    st.session_state.is_cached = resp_data.get("cached", False)
                    
                    if st.session_state.is_cached:
                        st.success(f"Duplicate file found! Fetching from cache... ID: `{st.session_state.task_id}`")
                    else:
                        st.success(f"Task submitted! ID: `{st.session_state.task_id}`")
                else:
                    st.error(f"API Error ({response.status_code}): {response.text}")
                    
            except requests.exceptions.ConnectionError:
                st.error("Could not connect to the API. Is the FastAPI server running?")

# 2. Polling loop outside the button click
if st.session_state.task_id and not st.session_state.results:
    status_placeholder = st.empty()
    
    with st.spinner("Retrieving from cache..." if st.session_state.is_cached else "Worker is processing your file..."):
        start_time = time.time()
        while True:
            try:
                poll_resp = requests.get(f"{API_URL}/{st.session_state.task_id}")
                if poll_resp.status_code == 200:
                    poll_data = poll_resp.json()
                    status = poll_data.get("status")
                    
                    if status == "success":
                        st.session_state.results = poll_data.get("results", [])
                        st.session_state.processing_time = poll_data.get("processing_time")
                        st.session_state.evaluation_metrics = poll_data.get("evaluation_metrics")
                        st.session_state.retrieve_time = time.time() - start_time
                        
                        status_placeholder.empty() # clear status text
                        st.rerun() # rerun the script to cleanly show results
                    elif status == "failed":
                        error_msg = poll_data.get("error") or poll_data.get("detail", "Unknown error")
                        status_placeholder.error(f"Processing failed: {error_msg}")
                        break
                    else:
                        # Still processing
                        status_placeholder.info(f"Task status: {status.upper()}... Checking again in 2 seconds.")
                        time.sleep(2)
                else:
                    status_placeholder.error(f"Error checking status: {poll_resp.status_code}")
                    break
                    
            except Exception as e:
                status_placeholder.error(f"Polling error: {e}")
                break

# 3. Render results outside the button click
if st.session_state.results:
    
    if st.session_state.is_cached:
        st.success(f"Retrieved from cache in {st.session_state.retrieve_time:.3f}s! (Original processing time: {st.session_state.processing_time:.2f}s)")
    else:
        st.success(f"Processing complete! (Time: {st.session_state.processing_time:.2f}s)")
        
    st.divider()
    
    tab1, tab2 = st.tabs(["📄 Document Results", "💬 Chat with Document"])
    
    with tab1:
        if testing_phase:
            if st.session_state.evaluation_metrics:
                wer = st.session_state.evaluation_metrics.get('wer')
                cer = st.session_state.evaluation_metrics.get('cer')
                st.info(f"📊 **Evaluation Metrics** — **WER**: `{wer}%` | **CER**: `{cer}%`")
            else:
                st.warning("⚠️ Testing Phase is ON but no Ground Truth was provided, so metrics were not calculated.")
        
        for res in st.session_state.results:
            st.markdown(f"### Page {res['page']}")
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Preprocessed Image (Deskewed & Binarized)**")
                if res.get("image_base64"):
                    image_bytes = base64.b64decode(res["image_base64"])
                    img = Image.open(BytesIO(image_bytes))
                    st.image(img, use_container_width=True)
                else:
                    st.warning("No image returned by API.")
                
            with col2:
                if res.get("needs_review"):
                    st.warning(f"⚠️ Confidence is low ({res.get('confidence', 0):.2f}%). Review might be needed.")
                else:
                    st.success(f"✅ High confidence extraction ({res.get('confidence', 0):.2f}%).")
                    
                st.markdown(f"**PSM Mode Applied:** `{res.get('psm_mode', 'N/A')}`")
                
                st.markdown("**Extracted Text:**")
                st.text_area(label="Text", value=res.get("text", ""), height=300, key=f"text_{st.session_state.task_id}_{res['page']}", label_visibility="collapsed")
            
            st.divider()
    
    with tab2:
        st.markdown("### 💬 Ask Questions")
        st.markdown("Ask anything about the uploaded document. Our AI will search the document and generate an answer using Groq.")
        
        # Show chat history
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                if msg.get("metrics"):
                    st.caption(f"📊 Faithfulness: {msg['metrics'].get('faithfulness', 0.0):.2f} | Relevancy: {msg['metrics'].get('answer_relevancy', 0.0):.2f}")
            
        question = st.chat_input("Ask a question about the document...")
        if question:
            st.chat_message("user").write(question)
            st.session_state.chat_history.append({"role": "user", "content": question})
            
            with st.spinner("Searching document & generating answer..."):
                try:
                    chat_resp = requests.post(f"{API_URL}/{st.session_state.task_id}/chat", json={"question": question})
                    if chat_resp.status_code == 200:
                        resp_data = chat_resp.json()
                        answer = resp_data.get("answer", "No answer received.")
                        metrics = resp_data.get("metrics", {})
                        
                        with st.chat_message("assistant"):
                            st.write(answer)
                            if metrics:
                                st.caption(f"📊 Faithfulness: {metrics.get('faithfulness', 0.0):.2f} | Relevancy: {metrics.get('answer_relevancy', 0.0):.2f}")
                        
                        st.session_state.chat_history.append({
                            "role": "assistant", 
                            "content": answer,
                            "metrics": metrics
                        })
                    else:
                        st.error(f"Failed to fetch answer. API returned {chat_resp.status_code}: {chat_resp.text}")
                except Exception as e:
                    st.error(f"Error querying chat API: {e}")
