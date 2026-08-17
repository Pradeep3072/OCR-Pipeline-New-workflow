import os
import cv2
import argparse
from preprocessor import convert_pdf_to_images, preprocess_image

def main(input_path, output_dir, poppler_path=None):
    if not os.path.exists(input_path):
        print(f"Error: Input file '{input_path}' not found.")
        return

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # 1. Identify Type & Route
    ext = os.path.splitext(input_path)[1].lower()
    
    images_to_process = []
    if ext == '.pdf':
        print("Detected PDF file.")
        images_to_process = convert_pdf_to_images(input_path, poppler_path)
    elif ext in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
        print("Detected Image file.")
        image = cv2.imread(input_path)
        if image is None:
             print(f"Error: Failed to read image '{input_path}'.")
             return
        images_to_process = [image]
    else:
        print(f"Unsupported file type: {ext}")
        return

    # 2. Image Pre-processing
    processed_images = []
    for i, img in enumerate(images_to_process):
        print(f"--- Processing Page {i+1} ---")
        processed_img = preprocess_image(img)
        processed_images.append(processed_img)
        
        # Save the preprocessed image for verification
        out_path = os.path.join(output_dir, f"preprocessed_page_{i+1}.png")
        cv2.imwrite(out_path, processed_img)
        print(f"Saved preprocessed image to: {out_path}")
        
    print("\nStep 2 completed successfully. Preprocessing done.")
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OCR Pipeline - Step 1 & 2")
    parser.add_argument("--input", required=True, help="Path to input PDF or Image file")
    parser.add_argument("--output_dir", default="output", help="Directory to save preprocessed images")
    parser.add_argument("--poppler_path", help="Path to poppler binaries (required for PDF on Windows if not in PATH)")
    
    args = parser.parse_args()
    main(args.input, args.output_dir, args.poppler_path)
