import streamlit as st
import os
import tempfile
from main import main as run_pipeline
from PIL import Image

st.set_page_config(page_title="OCR Pipeline Dashboard", layout="wide")

st.title("📄 OCR Pipeline Dashboard")
st.markdown("Upload an image or PDF to extract text using dynamic layout analysis and Tesseract OCR.")

uploaded_file = st.file_uploader("Choose a file (PDF, PNG, JPG, JPEG)", type=["pdf", "png", "jpg", "jpeg"])

if uploaded_file is not None:
    st.info(f"File uploaded: {uploaded_file.name}")
    
    if st.button("Run OCR Pipeline", type="primary"):
        with st.spinner("Processing document..."):
            # Save uploaded file to a temporary location
            temp_dir = tempfile.mkdtemp()
            input_path = os.path.join(temp_dir, uploaded_file.name)
            
            with open(input_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
                
            output_dir = os.path.join(temp_dir, "output")
            
            # Run the pipeline
            try:
                # We do not pass poppler_path here, so if testing PDFs on Windows it might fail
                # if Poppler is not in PATH.
                results = run_pipeline(input_path, output_dir)
                
                if not results:
                    st.error("No results returned. Ensure the file is valid.")
                else:
                    st.success(f"Processing complete! Found {len(results)} page(s).")
                    
                    st.divider()
                    
                    # Display results for each page
                    for res in results:
                        st.markdown(f"### Page {res['page']}")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("**Preprocessed Image (Deskewed & Binarized)**")
                            img = Image.open(res["image_path"])
                            st.image(img, use_container_width=True)
                            
                        with col2:
                            data = res["result_data"]
                            
                            # Display alerts based on confidence
                            if data["needs_review"]:
                                st.warning(f"⚠️ Confidence is low ({data['confidence']:.2f}%). Review might be needed.")
                            else:
                                st.success(f"✅ High confidence extraction ({data['confidence']:.2f}%).")
                                
                            st.markdown(f"**PSM Mode Applied:** `{data['psm_mode']}`")
                            
                            st.markdown("**Extracted Text:**")
                            st.text_area(label="Text", value=data["text"], height=300, key=f"text_{res['page']}", label_visibility="collapsed")
                        
                        st.divider()
                        
            except Exception as e:
                st.error(f"An error occurred during processing: {e}")
