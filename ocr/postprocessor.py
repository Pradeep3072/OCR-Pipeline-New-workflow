import json
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logger import get_logger

logger = get_logger(__name__)

def process_and_flag(text, confidence, psm_mode):
    """
    Step 5: Evaluates the OCR output and flags it for review if confidence is low.
    """
    needs_review = False
    
    # Check if confidence is below 70%
    if confidence < 70.0:
        logger.warning(f"  [Warning] Confidence ({confidence:.2f}%) is below 70%. Flagging for review.")
        needs_review = True
    else:
        logger.info(f"  [Success] High confidence extraction ({confidence:.2f}%).")
        
    result = {
        "text": text,
        "confidence": confidence,
        "psm_mode": psm_mode,
        "needs_review": needs_review
    }
    
    return result

def save_result(result, filepath):
    """
    Saves the structured dictionary to a JSON file.
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=4, ensure_ascii=False)
    logger.info(f"  Saved structured result to: {filepath}")
