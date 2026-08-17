import cv2
import numpy as np

font = cv2.FONT_HERSHEY_SIMPLEX

# 1. Sparse / Mixed Page (test_image.png)
img1 = np.ones((500, 500, 3), dtype=np.uint8) * 255
cv2.putText(img1, 'OCR Test Document', (50, 250), font, 1.2, (0, 0, 0), 2, cv2.LINE_AA)
cv2.imwrite('test_image.png', img1)

# 2. Single Row / Heading (test_heading.png)
# High aspect ratio (wide and short)
img2 = np.ones((50, 600, 3), dtype=np.uint8) * 255
cv2.putText(img2, 'Invoice Heading 123', (20, 35), font, 1.2, (0, 0, 0), 2, cv2.LINE_AA)
cv2.imwrite('test_heading.png', img2)

# 3. Multi-line Paragraph (test_paragraph.png)
# Multiple lines, dense text
img3 = np.ones((400, 600, 3), dtype=np.uint8) * 255
lines = [
    "This is a multi-line paragraph.",
    "It has several lines of text",
    "that should trigger the PSM 6",
    "heuristic because it has",
    "more than 1 line peak and",
    "a higher pixel density."
]
y = 50
for line in lines:
    cv2.putText(img3, line, (20, y), font, 1.0, (0, 0, 0), 2, cv2.LINE_AA)
    y += 50
cv2.imwrite('test_paragraph.png', img3)

print("Generated 3 test images.")
