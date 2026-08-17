import os
import cv2
import argparse
from preprocessor import convert_pdf_to_images, preprocess_image
from layout_analyzer import determine_psm
from ocr_engine import extract_text_and_confidence
from postprocessor import process_and_flag, save_result

def main(input_path, output_dir, poppler_path=None):
    if not os.path.exists(input_path):
        print(f"Error: Input file '{input_path}' not found.")
        return []

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # 1. Identify Type & Route
    ext = os.path.splitext(input_path)[1].lower()
    
    images_to_process = []
    if ext == '.pdf':
        print("Detected PDF file.")
        images_to_process = convert_pdf_to_images(input_path, poppler_path)
    elif ext in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.webp']:
        print("Detected Image file.")
        try:
            from PIL import Image
            import numpy as np
            pil_img = Image.open(input_path).convert('RGB')
            image = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        except Exception as e:
            print(f"Error: Failed to read image '{input_path}'. Exception: {e}")
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
        
        # Save the preprocessed image for debugging/verification
        out_img_path = os.path.join(output_dir, f"preprocessed_page_{i+1}.png")
        cv2.imwrite(out_img_path, processed_img)
        print(f"  Saved preprocessed image to: {out_img_path}")
        
        # 3. Dynamic PSM Switching
        psm_mode = determine_psm(processed_img)
        
        # 4. Execution & Verification (OCR)
        text, avg_conf = extract_text_and_confidence(processed_img, psm_mode)
        
        # 5. Flag for Post-Processing / Spellcheck & Output
        result = process_and_flag(text, avg_conf, psm_mode)
        
        out_json_path = os.path.join(output_dir, f"result_page_{i+1}.json")
        save_result(result, out_json_path)
        
        outputs.append({
            "page": i + 1,
            "image_path": out_img_path,
            "json_path": out_json_path,
            "result_data": result
        })
        
    print("\nOCR Pipeline completed successfully.")
    return outputs
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OCR Pipeline - Full Workflow")
    parser.add_argument("--input", required=True, help="Path to input PDF or Image file")
    parser.add_argument("--output_dir", default="output", help="Directory to save preprocessed images and JSON results")
    parser.add_argument("--poppler_path", help="Path to poppler binaries (required for PDF on Windows if not in PATH)")
    
    args = parser.parse_args()
    main(args.input, args.output_dir, args.poppler_path)
