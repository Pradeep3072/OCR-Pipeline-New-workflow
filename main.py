import os
import cv2
import argparse
import uuid
import shutil
from preprocessor import convert_pdf_to_images, preprocess_image
from layout_analyzer import determine_psm
from ocr_engine import extract_text_and_confidence
from postprocessor import process_and_flag, save_result
from s3_utils import download_file_from_s3, upload_file_to_s3

def main(s3_input_key, poppler_path=None):
    temp_dir = f"/tmp/{uuid.uuid4()}"
    os.makedirs(temp_dir, exist_ok=True)
    
    input_filename = os.path.basename(s3_input_key)
    local_input_path = os.path.join(temp_dir, input_filename)
    
    # Download file from S3
    try:
        download_file_from_s3(s3_input_key, local_input_path)
    except Exception as e:
        print(f"Error downloading {s3_input_key} from S3: {e}")
        return []

    # 1. Identify Type & Route
    ext = os.path.splitext(local_input_path)[1].lower()
    
    images_to_process = []
    if ext == '.pdf':
        print("Detected PDF file.")
        images_to_process = convert_pdf_to_images(local_input_path, poppler_path)
    elif ext in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.webp']:
        print("Detected Image file.")
        try:
            from PIL import Image
            import numpy as np
            pil_img = Image.open(local_input_path).convert('RGB')
            image = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        except Exception as e:
            print(f"Error: Failed to read image '{local_input_path}'. Exception: {e}")
            return []
            
        images_to_process = [image]
    else:
        print(f"Unsupported file type: {ext}")
        return []

    # Process each page
    outputs = []
    for i, img in enumerate(images_to_process):
        print(f"\n--- Processing Page {i+1} ---")
        
        # 2. Image Pre-processing
        processed_img = preprocess_image(img)
        
        # Save the preprocessed image temporarily
        temp_img_path = os.path.join(temp_dir, f"preprocessed_page_{i+1}.png")
        cv2.imwrite(temp_img_path, processed_img)
        
        # Upload preprocessed image to S3
        s3_image_key = f"output/{os.path.splitext(input_filename)[0]}_page_{i+1}.png"
        upload_file_to_s3(temp_img_path, s3_image_key)
        
        # 3. Dynamic PSM Switching
        psm_mode = determine_psm(processed_img)
        
        # 4. Execution & Verification (OCR)
        text, avg_conf = extract_text_and_confidence(processed_img, psm_mode)
        
        # 5. Flag for Post-Processing / Spellcheck & Output
        result = process_and_flag(text, avg_conf, psm_mode)
        
        outputs.append({
            "page": i + 1,
            "image_s3_key": s3_image_key,
            "result_data": result
        })
        
    # Clean up temp dir
    try:
        shutil.rmtree(temp_dir)
    except Exception as e:
        print(f"Warning: Failed to clean up temp dir {temp_dir}: {e}")
        
    print("\nOCR Pipeline completed successfully.")
    return outputs
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OCR Pipeline - Full Workflow")
    parser.add_argument("--s3_key", required=True, help="S3 Object Key to process")
    parser.add_argument("--poppler_path", help="Path to poppler binaries")
    
    args = parser.parse_args()
    main(args.s3_key, args.poppler_path)
