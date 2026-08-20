import jiwer
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logger import get_logger

logger = get_logger(__name__)

def calculate_metrics(predicted_text: str, ground_truth_text: str):
    """
    Calculates WER (Word Error Rate) and CER (Character Error Rate).
    Returns a dictionary with 'wer' and 'cer' as percentages.
    """
    if not predicted_text or not ground_truth_text:
        return {"wer": 0.0, "cer": 0.0}
        
    try:
        # Calculate WER and CER
        wer = jiwer.wer(ground_truth_text, predicted_text) * 100.0
        cer = jiwer.cer(ground_truth_text, predicted_text) * 100.0
        
        logger.info(f"Evaluation Metrics - WER: {wer:.2f}%, CER: {cer:.2f}%")
        return {"wer": round(wer, 2), "cer": round(cer, 2)}
    except Exception as e:
        logger.error(f"Error calculating metrics: {e}")
        return {"wer": None, "cer": None}
