import cv2
import numpy as np

# Create a white image
img = np.ones((500, 500, 3), dtype=np.uint8) * 255

# Add some text
font = cv2.FONT_HERSHEY_SIMPLEX
cv2.putText(img, 'OCR Test Document', (50, 250), font, 1.2, (0, 0, 0), 2, cv2.LINE_AA)

# Save it
cv2.imwrite('test_image.png', img)
print("Created test_image.png")
