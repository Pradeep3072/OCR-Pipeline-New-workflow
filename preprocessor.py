import os
import cv2
import numpy as np
from pdf2image import convert_from_path

def convert_pdf_to_images(pdf_path, poppler_path=None):
    """
    Converts a PDF file to a list of OpenCV images (numpy arrays).
    """
    print(f"Converting {pdf_path} to images...")
    try:
        # Convert to PIL images
        pil_images = convert_from_path(pdf_path, poppler_path=poppler_path)
    except Exception as e:
        print("Error converting PDF. Ensure poppler is installed and in your PATH, or provide --poppler_path.")
        raise e
        
    cv_images = []
    for pil_image in pil_images:
        # Convert PIL image to OpenCV format (RGB to BGR)
        cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        cv_images.append(cv_image)
        
    return cv_images

def binarize_and_clear_noise(image):
    """
    Applies binarization and morphological operations to clear noise.
    """
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply adaptive thresholding for binarization
    # It handles uneven illumination better than global thresholding
    binary = cv2.adaptiveThreshold(
        gray, 255, 
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY_INV, 
        11, 2
    )
    
    # Optional: Apply some morphological operations to remove small noise
    kernel = np.ones((1, 1), np.uint8)
    opening = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)
    
    return opening

def detect_and_fix_skew(image):
    """
    Detects the skew angle of the text and rotates the image to correct it.
    Input should be a binarized image (white text on black background).
    """
    # Grab the (x, y) coordinates of all pixel values that are greater than zero (white)
    coords = np.column_stack(np.where(image > 0))
    
    # Compute the minimum bounding box
    if len(coords) == 0:
        return image, 0.0
        
    angle = cv2.minAreaRect(coords)[-1]

    # The `cv2.minAreaRect` function returns values in the range [-90, 0)
    # As the rectangle rotates clockwise the returned angle trends to 0
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    # If the angle is very small, we just assume it's straight
    if abs(angle) < 0.5:
        return image, 0.0

    # Rotate the image to deskew it
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    
    # Perform the rotation
    rotated = cv2.warpAffine(
        image, M, (w, h),
        flags=cv2.INTER_CUBIC, 
        borderMode=cv2.BORDER_REPLICATE
    )
    
    return rotated, angle
    
def preprocess_image(image):
    """
    Full pipeline for step 2: Binarize -> Denoise -> Deskew
    """
    print("  Applying binarization and noise reduction...")
    binarized = binarize_and_clear_noise(image)
    
    print("  Detecting and fixing skew...")
    deskewed, angle = detect_and_fix_skew(binarized)
    print(f"  Deskew angle: {angle:.2f} degrees")
    
    # Convert back to standard binarized (black text on white bg) for further steps
    final_image = cv2.bitwise_not(deskewed)
    return final_image
