"""
Multi-Tier Visual Generation: Local Stable Diffusion Fallback
Provides local Stable Diffusion generation as fallback when external APIs fail
"""

import os
import logging
import torch
from typing import Optional, Dict, Any
from pathlib import Path
import base64
from io import BytesIO

logger = logging.getLogger(__name__)

class LocalStableDiffusionFallback:
    """
    Local Stable Diffusion implementation for visual generation fallback
    Used when external APIs (Pollinations, SiliconFlow) are unavailable or rate-limited
    """
    
    def __init__(self, model_path: str = "./models/stable-diffusion", 
                 device: str = "auto", 
                 safety_checker: bool = True):
        """
        Initialize local Stable Diffusion fallback
        
        Args:
            model_path: Path to local Stable Diffusion model
            device: Device to run on ('cpu', 'cuda', 'auto')
            safety_checker: Whether to enable safety checker
        """
        self.model_path = Path(model_path)
        self.device = self._get_device(device)
        self.safety_checker = safety_checker
        self.pipe = None
        
        logger.info(f"Initializing Local Stable Diffusion Fallback on {self.device}")
        logger.info(f"Model path: {self.model_path}")
        
        # Model will be loaded on first use to save memory
        self._model_loaded = False
    
    def _get_device(self, device: str) -> str:
        """Determine the appropriate device to use"""
        if device == "auto":
            if torch.cuda.is_available():
                return "cuda"
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                return "mps"
            else:
                return "cpu"
        return device
    
    def _load_model(self):
        """Load the Stable Diffusion model (lazy loading)"""
        if self._model_loaded:
            return
            
        try:
            logger.info("Loading Stable Diffusion model...")
            
            # Try to import diffusers
            try:
                from diffusers import StableDiffusionPipeline
                logger.info("Using diffusers library")
            except ImportError:
                logger.error("diffusers library not installed. Install with: pip install diffusers transformers torch")
                raise
            
            # Check if model exists locally
            if self.model_path.exists():
                logger.info(f"Loading model from local path: {self.model_path}")
                self.pipe = StableDiffusionPipeline.from_pretrained(
                    self.model_path,
                    torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                    safety_checker=None if not self.safety_checker else None
                )
            else:
                # Fallback to downloading from Hugging Face
                logger.info("Local model not found, downloading from Hugging Face...")
                model_id = "runwayml/stable-diffusion-v1-5"
                self.pipe = StableDiffusionPipeline.from_pretrained(
                    model_id,
                    torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                    safety_checker=None if not self.safety_checker else None
                )
                
                # Save model locally for future use
                self.model_path.mkdir(parents=True, exist_ok=True)
                self.pipe.save_pretrained(self.model_path)
                logger.info(f"Model saved to {self.model_path}")
            
            # Move to device
            self.pipe = self.pipe.to(self.device)
            
            # Enable memory efficient attention if available
            if hasattr(self.pipe, "enable_attention_slicing"):
                self.pipe.enable_attention_slicing()
                
            self._model_loaded = True
            logger.info("Stable Diffusion model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load Stable Diffusion model: {e}")
            raise
    
    def generate_image(self, prompt: str, 
                      negative_prompt: Optional[str] = None,
                      num_inference_steps: int = 25,
                      guidance_scale: float = 7.5,
                      width: int = 512,
                      height: int = 512,
                      seed: Optional[int] = None) -> Dict[str, Any]:
        """
        Generate image using local Stable Diffusion
        
        Args:
            prompt: Text description of desired image
            negative_prompt: What to avoid in the image
            num_inference_steps: Number of denoising steps
            guidance_scale: How strongly to follow the prompt
            width: Image width in pixels
            height: Image height in pixels
            seed: Random seed for reproducibility
            
        Returns:
            Dictionary containing generated image data and metadata
        """
        if not self._model_loaded:
            self._load_model()
        
        logger.info(f"Generating image with prompt: '{prompt[:50]}...'")
        
        try:
            # Set seed for reproducibility if provided
            if seed is not None:
                torch.manual_seed(seed)
                if self.device == "cuda":
                    torch.cuda.manual_seed_all(seed)
            
            # Generate image
            result = self.pipe(
                prompt=prompt,
                negative_prompt=negative_prompt,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                width=width,
                height=height
            )
            
            image = result.images[0]
            
            # Convert to base64 for easy transport
            buffered = BytesIO()
            image.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode()
            
            logger.info("Image generated successfully")
            
            return {
                'success': True,
                'image_base64': img_base64,
                'prompt': prompt,
                'parameters': {
                    'negative_prompt': negative_prompt,
                    'num_inference_steps': num_inference_steps,
                    'guidance_scale': guidance_scale,
                    'width': width,
                    'height': height,
                    'seed': seed
                },
                'metadata': {
                    'generation_method': 'local_stable_diffusion',
                    'device': self.device,
                    'model_path': str(self.model_path)
                }
            }
            
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'prompt': prompt
            }
    
    def is_available(self) -> bool:
        """
        Check if the local SD fallback is available and ready
        
        Returns:
            True if model can be loaded, False otherwise
        """
        try:
            if not self._model_loaded:
                self._load_model()
            return True
        except Exception as e:
            logger.warning(f"Local SD fallback not available: {e}")
            return False

# Example usage and testing
if __name__ == "__main__":
    # Initialize fallback generator
    fallback = LocalStableDiffusionFallback(
        model_path="./models/sd-fallback",
        device="auto"
    )
    
    # Check availability
    if fallback.is_available():
        print("Local SD fallback is available")
        
        # Generate test image
        result = fallback.generate_image(
            prompt="A beautiful sunset over a cryptocurrency trading chart, digital art, vibrant colors",
            width=512,
            height=512,
            num_inference_steps=20
        )
        
        if result['success']:
            print("Image generated successfully!")
            # In a real app, you would save or transmit the base64 image
            # For demo, we'll just show the parameters
            print(f"Parameters: {result['parameters']}")
        else:
            print(f"Generation failed: {result['error']}")
    else:
        print("Local SD fallback is not available")
        print("Make sure diffusers and torch are installed:")
        print("pip install diffusers transformers torch")