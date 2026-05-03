#!/usr/bin/env python3
"""
Human AI: OCRAgent - v1.1
Specialized agent for Optical Character Recognition (OCR).
Extracts text from images (PNG, JPG, JPEG) to provide structured text for the swarm.
Includes an OpenCV preprocessing pipeline to improve Tesseract accuracy.
"""

import os
import cv2
import numpy as np
from typing import Optional
from pathlib import Path

# Third-party library imports
try:
    from PIL import Image
    import pytesseract
except ImportError:
    # These will be installed via the venv
    pass

class OCRAgent:
    def __init__(self, output_dir: str = "/home/yahwehatwork/human-ai/docs/converted"):
        """Initialize OCRAgent.
        If the specified output_dir is not writable, fall back to the workspace
        directory (/home/yahwehatwork/.openclaw/workspace) to ensure write
        operations succeed.
        """
        self.output_dir = output_dir
        # Verify writability; if not, fallback
        try:
            os.makedirs(self.output_dir, exist_ok=True)
            test_path = os.path.join(self.output_dir, "__write_test__")
            with open(test_path, "w") as _:
                pass
            os.remove(test_path)
        except Exception:
            fallback = "/home/yahwehatwork/.openclaw/workspace"
            os.makedirs(fallback, exist_ok=True)
            self.output_dir = fallback


    def _preprocess_image(self, image_path: str) -> Optional[np.ndarray]:
        """
        Preprocessing pipeline to improve OCR accuracy:
        1. Grayscale conversion
        2. Gaussian Blur (noise reduction)
        3. Adaptive Thresholding (lighting/contrast normalization)
        """
        try:
            # Load image using OpenCV
            image = cv2.imread(image_path)
            if image is None:
                print(f"❌ Error: OpenCV could not read image {image_path}")
                return None

            # 1. Grayscale conversion
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # 2. Gaussian Blur to reduce noise
            # (5, 5) is a standard kernel size for moderate noise reduction
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)

            # 3. Adaptive Thresholding
            # Handles varying lighting conditions by calculating threshold for small regions
            processed = cv2.adaptiveThreshold(
                blurred, 
                255, 
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 
                11, 
                2
            )

            return processed
        except Exception as e:
            print(f"❌ Preprocessing error for {image_path}: {e}")
            return None

    def extract_text(self, image_path: str) -> Optional[str]:
        """
        Performs OCR on the provided image file after applying a preprocessing pipeline.
        Returns the extracted text.
        """
        if not os.path.exists(image_path):
            print(f"❌ Error: Image {image_path} not found.")
            return None

        ext = Path(image_path).suffix.lower()
        supported_exts = ['.png', '.jpg', '.jpeg', '.bmp', '.tiff']
        if ext not in supported_exts:
            print(f"⚠️ Unsupported image format {ext}. Attempting OCR anyway...")

        filename = Path(image_path).stem
        target_path = os.path.join(self.output_dir, f"{filename}_ocr.txt")

        try:
            # Apply the OpenCV preprocessing pipeline
            processed_img = self._preprocess_image(image_path)
            
            if processed_img is not None:
                # Use the processed image (numpy array) directly with pytesseract
                text = pytesseract.image_to_string(processed_img)
            else:
                # Fallback to original image if preprocessing fails
                print(f"⚠️ Preprocessing failed for {image_path}, falling back to raw image.")
                text = pytesseract.image_to_string(Image.open(image_path))
            
            if text and text.strip():
                with open(target_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                return text
            else:
                print(f"⚠️ No text extracted from {image_path}")
                return None
                
        except Exception as e:
            print(f"❌ OCR error for {image_path}: {e}")
            return None

    async def close(self):
        """Placeholder for async cleanup."""
        pass

if __name__ == "__main__":
    # Basic internal test
    agent = OCRAgent()
    print("OCRAgent initialized. Ready to process images with OpenCV preprocessing.")
