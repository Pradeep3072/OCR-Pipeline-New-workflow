import pytesseract
from pytesseract import Output
import numpy as np
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logger import get_logger

logger = get_logger(__name__)

def extract_text_and_confidence(image, psm_mode):
    """
    Step 4: Executes Tesseract OCR on the image with the specified PSM mode.
    Returns the extracted text and the average confidence score.
    """
    custom_config = f'--psm {psm_mode}'
    logger.info(f"  Executing Tesseract with config: {custom_config}")
    
    try:
        # data contains bounding boxes, confidences, and text for each word
        data = pytesseract.image_to_data(image, config=custom_config, output_type=Output.DICT)
    except pytesseract.TesseractNotFoundError:
        logger.error("\n[ERROR] Tesseract-OCR is not installed or not in your PATH.")
        logger.error("Please install it from https://github.com/UB-Mannheim/tesseract/wiki and restart your terminal.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n[ERROR] OCR Failed: {e}")
        sys.exit(1)
        
    confidences = []
    
    # data['conf'] contains confidence per word (-1 for empty/blocks)
    for i in range(len(data['text'])):
        conf = int(data['conf'][i])
        word = data['text'][i].strip()
        
        if conf >= 0 and word:
            confidences.append(conf)
            
    # Calculate average confidence
    avg_confidence = float(np.mean(confidences)) if confidences else 0.0
    
    # We use image_to_string to get the properly formatted full text (preserves layout better)
    full_text = pytesseract.image_to_string(image, config=custom_config).strip()
    
    return full_text, avg_confidence
