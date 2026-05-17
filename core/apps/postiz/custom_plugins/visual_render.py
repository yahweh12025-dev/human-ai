"""
Multi-Tier Visual Generation: SiliconFlow Final Render
Handles final high-quality visual rendering using SiliconFlow API
"""

import os
import logging
import requests
import json
from typing import Dict, List, Optional, Any
from pathlib import Path
import base64
from io import BytesIO

logger = logging.getLogger(__name__)

class SiliconFlowRenderer:
    """
    Final visual rendering using SiliconFlow API
    Produces high-quality, polished visuals from draft concepts
    """
    
    def __init__(self, api_key: str, api_url: str = "https://api.siliconflow.cn/v1"):
        """
        Initialize SiliconFlow rendering service
        
        Args:
            api_key: API key for SiliconFlow service
            api_url: Base URL for SiliconFlow API
        """
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        logger.info(f"SiliconFlowRenderer initialized with API: {self.api_url}")
    
    def _make_request(self, prompt: str, width: int = 1024, height: int = 1024,
                     model: str = "StableDiffusionXL", 
                     num_inference_steps: int = 50,
                     guidance_scale: float = 7.5,
                     seed: Optional[int] = None) -> Dict[str, Any]:
        """
        Make request to SiliconFlow API for high-quality image generation
        
        Args:
            prompt: Text description for image generation
            width: Image width in pixels
            height: Image height in pixels
            model: AI model to use
            num_inference_steps: Number of denoising steps for quality
            guidance_scale: How strongly to follow the prompt
            seed: Random seed for reproducibility
            
        Returns:
            Dictionary with image data or error information
        """
        # Prepare request payload
        payload = {
            "model": model,
            "prompt": prompt,
            "width": width,
            "height": height,
            "num_inference_steps": num_inference_steps,
            "guidance_scale": guidance_scale,
        }
        
        if seed is not None:
            payload["seed"] = seed
        
        try:
            logger.info(f"Making request to SiliconFlow API for: {prompt[:50]}...")
            response = requests.post(
                f"{self.api_url}/image/generate",
                headers=self.headers,
                json=payload,
                timeout=60  # SiliconFlow might take longer for high-quality renders
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Extract image data from response
            if 'images' in result and len(result['images']) > 0:
                # Assuming the API returns base64 encoded images
                image_base64 = result['images'][0]
                image_data = base64.b64decode(image_base64)
                
                return {
                    'success': True,
                    'image_data': image_data,
                    'prompt': prompt,
                    'parameters': {
                        'width': width,
                        'height': height,
                        'model': model,
                        'num_inference_steps': num_inference_steps,
                        'guidance_scale': guidance_scale,
                        'seed': seed
                    }
                }
            else:
                logger.error(f"Unexpected response format from SiliconFlow: {result}")
                return {
                    'success': False,
                    'error': 'Unexpected response format from API',
                    'prompt': prompt
                }
            
        except requests.exceptions.Timeout:
            logger.error("SiliconFlow API request timed out")
            return {
                'success': False,
                'error': 'API request timed out',
                'prompt': prompt
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"SiliconFlow API request failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'prompt': prompt
            }
        except Exception as e:
            logger.error(f"Unexpected error in SiliconFlow request: {e}")
            return {
                'success': False,
                'error': str(e),
                'prompt': prompt
            }
    
    def render_final_visual(self, draft_prompt: str, 
                          enhancement_prompt: str = "",
                          width: int = 1024, height: int = 1024) -> Dict[str, Any]:
        """
        Render final high-quality visual based on draft concept
        
        Args:
            draft_prompt: Base prompt from drafting phase
            enhancement_prompt: Additional quality enhancements
            width: Final image width
            height: Final image height
            
        Returns:
            Dictionary with final rendered image data
        """
        # Combine draft prompt with enhancements for final render
        full_prompt = draft_prompt
        if enhancement_prompt:
            full_prompt += f", {enhancement_prompt}"
        
        # Add quality enhancements for final render
        quality_enhancements = [
            "ultra detailed",
            "8k resolution",
            "professional photography",
            "sharp focus",
            "vibrant colors",
            "award winning"
        ]
        
        full_prompt += ", " + ", ".join(quality_enhancements)
        
        # Make the API call with higher quality settings
        result = self._make_request(
            prompt=full_prompt,
            width=width,
            height=height,
            model="StableDiffusionXL",
            num_inference_steps=50,  # Higher quality = more steps
            guidance_scale=7.5
        )
        
        if result.get('success'):
            logger.info("Final render completed successfully")
        else:
            logger.error(f"Final render failed: {result.get('error')}")
        
        return result
    
    def process_draft_to_final(self, draft_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a draft concept through to final render
        
        Args:
            draft_data: Draft result from PollinationsDrafting
            
        Returns:
            Final render result
        """
        if not draft_data.get('success', False):
            logger.warning("Cannot process failed draft")
            return draft_data
        
        # We don't have direct access to the prompt from the binary image data
        # In a real implementation, we'd store the prompt with the draft
        # For now, we'll create a generic enhancement prompt
        
        # Extract information we do have
        signal_type = draft_data.get('signal_type', 'NEUTRAL')
        symbol = draft_data.get('symbol', 'CRYPTO')
        
        # Create enhancement prompt based on signal type
        enhancement_map = {
            'BUY': "bullish momentum, upward trending chart, green growth accents",
            'SELL': "bearish pressure, downward trending chart, red decline accents", 
            'WATCH': "consolidation pattern, sideways movement, neutral tones",
            'NEUTRAL': "balanced composition, neutral market sentiment"
        }
        
        enhancement = enhancement_map.get(signal_type, "professional financial visualization")
        
        # For demo purposes, we'll use a placeholder prompt
        # In reality, we'd need to store/reconstruct the original prompt
        draft_prompt = f"{symbol} {signal_type} trading signal, professional financial chart, cryptocurrency theme"
        
        logger.info(f"Processing draft to final render for {signal_type} signal on {symbol}")
        
        # Render final version
        return self.render_final_visual(
            draft_prompt=draft_prompt,
            enhancement_prompt=enhancement,
            width=1024,
            height=1024
        )

# Example usage
if __name__ == "__main__":
    # Example initialization (would normally come from config/secrets)
    # renderer = SiliconFlowRenderer(api_key="your-siliconflow-api-key")
    
    # Example draft prompt (normally would come from draft phase)
    example_draft_prompt = "ETH BUY signal, upward trend with green accents, professional trading chart"
    
    # Example enhancement prompt
    example_enhancement = "ultra detailed, 8k resolution, award winning financial visualization"
    
    print("SiliconFlow Renderer initialized")
    print("Note: Actual rendering requires a valid SiliconFlow API key")
    print(f"Example prompt: {example_draft_prompt}")
    print(f"Example enhancement: {example_enhancement}")