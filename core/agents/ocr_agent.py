#!/usr/bin/env python3
"""
Human AI: OCRAgent - v1.0
Specialized agent for Optical Character Recognition (OCR).
Extracts text from images (PNG, JPG, JPEG) to provide structured text for the swarm.
"""

import os
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
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def extract_text(self, image_path: str) -> Optional[str]:
        """
        Performs OCR on the provided image file and returns the extracted text.
        """
        if not os.path.exists(image_path):
            print(f"❌ Error: Image {image_path} not found.")
            return None

        ext = Path(image_path).suffix.lower()
        if ext not in ['.png', '.jpg', '.jpeg', '.bmp', '.tiff']:
            print(f"⚠️ Unsupported image format {ext}. Attempting OCR anyway...")

        filename = Path(image_path).stem
        target_path = os.path.join(self.output_dir, f"{filename}_ocr.txt")

        try:
            # Use Tesseract for OCR
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
    print("OCRAgent initialized. Ready to process images.")
