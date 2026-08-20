import cv2
import numpy as np
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logger import get_logger

logger = get_logger(__name__)

def calculate_pixel_density(image):
    """
    Calculates the ratio of foreground (text) pixels to total pixels in the image.
    The input image is black text on white background (from Step 2).
    """
    total_pixels = image.shape[0] * image.shape[1]
    if total_pixels == 0:
        return 0
        
    # Invert to make text white (255) for counting
    inverted = cv2.bitwise_not(image)
    text_pixels = cv2.countNonZero(inverted)
    
    return (text_pixels / total_pixels) * 100

def get_line_peaks(image):
    """
    Calculates the horizontal projection profile to count the number of text lines.
    """
    inverted = cv2.bitwise_not(image)
    
    # Sum along the rows
    horizontal_projection = np.sum(inverted, axis=1)
    
    # A row with text will have a sum > threshold
    # 255 * 5 means at least 5 white pixels to count as part of a line
    threshold = 255 * 5 
    
    peaks = 0
    in_peak = False
    
    for val in horizontal_projection:
        if val > threshold:
            if not in_peak:
                peaks += 1
                in_peak = True
        else:
            in_peak = False
            
    return peaks

def determine_psm(image):
    """
    Step 3: Heuristic Layout Analysis to determine PSM.
    """
    height, width = image.shape[:2]
    aspect_ratio = width / height if height > 0 else 0
    
    line_peaks = get_line_peaks(image)
    pixel_density = calculate_pixel_density(image)
    
    logger.debug(f"  [Layout Analysis] Height: {height}px, Aspect Ratio: {aspect_ratio:.2f}")
    logger.debug(f"  [Layout Analysis] Line peaks: {line_peaks}, Pixel Density: {pixel_density:.2f}%")
    
    # PSM 7 (Single Row/Heading): Height < 60px OR (aspect ratio is horizontally stretched AND line peaks <= 1).
    if height < 60 or (aspect_ratio > 3.0 and line_peaks <= 1):
        logger.info("  => Selected PSM 7 (Single Row / Heading)")
        return 7
        
    # PSM 6 (Multi-line Paragraph): Line peaks > 1 AND pixel density >= 5%
    if line_peaks > 1 and pixel_density >= 5.0:
        logger.info("  => Selected PSM 6 (Multi-line Paragraph)")
        return 6
        
    # PSM 3 (Sparse / Mixed Page): Default/fallback
    logger.info("  => Selected PSM 3 (Sparse / Mixed Page)")
    return 3
