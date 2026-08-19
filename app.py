import streamlit as st
import requests
import base64
import time
from io import BytesIO
from PIL import Image

import os

st.set_page_config(page_title="OCR Pipeline Dashboard", layout="wide")

st.title("📄 OCR Distributed Pipeline")
st.markdown("Upload an image or PDF to extract text using our distributed Celery+Redis backend.")

# FastAPI endpoint URL
API_URL = os.getenv("API_URL", "http://localhost:8000/ocr")

uploaded_file = st.file_uploader("Choose a file (PDF, PNG, JPG, JPEG, WEBP)", type=["pdf", "png", "jpg", "jpeg", "webp"])

if uploaded_file is not None:
    st.info(f"File uploaded: {uploaded_file.name}")
    
    if st.button("Run OCR Pipeline", type="primary"):
        task_id = None
        
        # 1. Submit the file and get a task ID
        with st.spinner("Submitting document to the queue..."):
            try:
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                response = requests.post(API_URL, files=files)
                
                if response.status_code == 200:
                    data = response.json()
                    task_id = data.get("task_id")
                    st.success(f"Task submitted! ID: `{task_id}`")
                else:
                    st.error(f"API Error ({response.status_code}): {response.text}")
                    st.stop()
                    
            except requests.exceptions.ConnectionError:
                st.error("Could not connect to the API. Is the FastAPI server running?")
                st.stop()
        
        # 2. Poll the API for the result
        if task_id:
            status_placeholder = st.empty()
            results = None
            
            with st.spinner("Worker is processing your file..."):
                while True:
                    try:
                        poll_resp = requests.get(f"{API_URL}/{task_id}")
                        if poll_resp.status_code == 200:
                            poll_data = poll_resp.json()
                            status = poll_data.get("status")
                            
                            if status == "success":
                                results = poll_data.get("results", [])
                                status_placeholder.success("Processing complete!")
                                break
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
            
            # 3. Render results
            if results:
                st.divider()
                for res in results:
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
                        st.text_area(label="Text", value=res.get("text", ""), height=300, key=f"text_{res['page']}", label_visibility="collapsed")
                    
                    st.divider()
