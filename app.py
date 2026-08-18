import streamlit as st
import requests
import base64
from io import BytesIO
from PIL import Image

st.set_page_config(page_title="OCR Pipeline Dashboard", layout="wide")

st.title("📄 OCR Pipeline Dashboard")
st.markdown("Upload an image or PDF to extract text using our new FastAPI backend.")

# FastAPI endpoint URL
API_URL = "http://localhost:8000/ocr"

uploaded_file = st.file_uploader("Choose a file (PDF, PNG, JPG, JPEG, WEBP)", type=["pdf", "png", "jpg", "jpeg", "webp"])

if uploaded_file is not None:
    st.info(f"File uploaded: {uploaded_file.name}")
    
    if st.button("Run OCR Pipeline", type="primary"):
        with st.spinner("Processing document via API..."):
            try:
                # Send the file to the FastAPI backend
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                response = requests.post(API_URL, files=files)
                
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    
                    if not results:
                        st.error("No results returned from the API.")
                    else:
                        st.success(f"Processing complete! Found {len(results)} page(s).")
                        st.divider()
                        
                        # Display results for each page
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
                                # Display alerts based on confidence
                                if res.get("needs_review"):
                                    st.warning(f"⚠️ Confidence is low ({res.get('confidence', 0):.2f}%). Review might be needed.")
                                else:
                                    st.success(f"✅ High confidence extraction ({res.get('confidence', 0):.2f}%).")
                                    
                                st.markdown(f"**PSM Mode Applied:** `{res.get('psm_mode', 'N/A')}`")
                                
                                st.markdown("**Extracted Text:**")
                                st.text_area(label="Text", value=res.get("text", ""), height=300, key=f"text_{res['page']}", label_visibility="collapsed")
                            
                            st.divider()
                else:
                    st.error(f"API Error ({response.status_code}): {response.text}")
                    
            except requests.exceptions.ConnectionError:
                st.error("Could not connect to the API. Is the FastAPI server running? (Try running `uvicorn api:app --reload` in another terminal)")
            except Exception as e:
                st.error(f"An error occurred: {e}")
