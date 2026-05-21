"""
Multi-Tier Visual Generation: Pollinations Drafting
Handles initial visual concept generation using Pollinations AI API
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

class PollinationsDrafting:
    """
    Initial visual concept generation using Pollinations AI
    Creates multiple draft options for visual content based on trading signals
    """
    
    def __init__(self, api_url: str = "https://text.pollinations.ai/", 
                 timeout: int = 30):
        """
        Initialize Pollinations drafting service
        
        Args:
            api_url: Base URL for Pollinations API
            timeout: Request timeout in seconds
        """
        self.api_url = api_url.rstrip('/')
        self.timeout = timeout
        logger.info(f"PollinationsDrafting initialized with API: {self.api_url}")
    
    def _make_request(self, prompt: str, width: int = 512, height: int = 512,
                     model: str = "flux", seed: Optional[int] = None) -> Dict[str, Any]:
        """
        Make request to Pollinations AI for image generation
        
        Args:
            prompt: Text description for image generation
            width: Image width in pixels
            height: Image height in pixels
            model: AI model to use (default: flux)
            seed: Random seed for reproducibility
            
        Returns:
            Dictionary with image data or error information
        """
        # Prepare parameters
        params = {
            'prompt': prompt,
            'width': width,
            'height': height,
            'model': model,
            'nologo': True,
            'private': True,
            'enhance': True
        }
        
        if seed is not None:
            params['seed'] = seed
        
        try:
            logger.info(f"Making request to Pollinations API for: {prompt[:50]}...")
            response = requests.get(
                self.api_url,
                params=params,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            
            # Return image data
            return {
                'success': True,
                'image_data': response.content,
                'content_type': response.headers.get('content-type', 'image/png'),
                'prompt': prompt,
                'parameters': {
                    'width': width,
                    'height': height,
                    'model': model,
                    'seed': seed
                }
            }
            
        except requests.exceptions.Timeout:
            logger.error("Pollinations API request timed out")
            return {
                'success': False,
                'error': 'API request timed out',
                'prompt': prompt
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Pollinations API request failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'prompt': prompt
            }
        except Exception as e:
            logger.error(f"Unexpected error in Pollinations request: {e}")
            return {
                'success': False,
                'error': str(e),
                'prompt': prompt
            }
    
    def generate_trading_visual_drafts(self, signal_data: Dict[str, Any], 
                                     num_drafts: int = 4) -> List[Dict[str, Any]]:
        """
        Generate multiple visual draft concepts based on trading signal data
        
        Args:
            signal_data: Dictionary containing trading signal information
            num_drafts: Number of draft variations to generate
            
        Returns:
            List of draft generation results
        """
        drafts = []
        
        # Extract key information from signal data
        signal_type = signal_data.get('signal', 'NEUTRAL')
        symbol = signal_data.get('symbol', 'BTC')
        confidence = signal_data.get('confidence', 0.5)
        reason = signal_data.get('reason', '')
        
        # Base prompt elements
        base_elements = [
            f"{symbol} trading signal",
            f"{signal_type} indication",
            "professional financial chart style",
            "cryptocurrency theme",
            "modern digital art"
        ]
        
        # Add confidence-based modifiers
        if confidence > 0.8:
            base_elements.append("high confidence, bold colors")
        elif confidence > 0.6:
            base_elements.append("medium confidence, balanced colors")
        else:
            base_elements.append("low confidence, subdued tones")
        
        # Add signal-specific elements
        if signal_type == 'BUY':
            base_elements.extend(["upward trend", "green accents", "bullish momentum"])
        elif signal_type == 'SELL':
            base_elements.extend(["downward trend", "red accents", "bearish pressure"])
        else:
            base_elements.extend(["consolidation", "neutral colors", "sideways movement"])
        
        # Create base prompt
        base_prompt = ", ".join(base_elements)
        
        # Generate multiple drafts with variations
        for i in range(num_drafts):
            # Vary the prompt slightly for each draft
            variation_prompts = [
                f"{base_prompt}, detailed technical analysis overlay",
                f"{base_prompt}, abstract representation with geometric patterns",
                f"{base_prompt}, minimalist design with clean lines",
                f"{base_prompt}, vibrant cyberpunk aesthetic",
                f"{base_prompt}, dark mode with glowing elements",
                f"{base_prompt}, light mode with soft gradients",
                f"{base_prompt}, includes volume indicators",
                f"{base_prompt}, shows support/resistance levels"
            ]
            
            # Select prompt variation (cycle through if we need more drafts than variations)
            prompt_index = i % len(variation_prompts)
            full_prompt = variation_prompts[prompt_index]
            
            # Add some randomness to seed for variation
            import random
            seed = random.randint(1, 999999) if i > 0 else 42  # Fixed seed for first draft
            
            # Generate the draft
            result = self._make_request(
                prompt=full_prompt,
                width=768,
                height=768,
                model="flux",
                seed=seed
            )
            
            # Add metadata
            result.update({
                'draft_id': i + 1,
                'signal_type': signal_type,
                'symbol': symbol,
                'confidence': confidence,
                'generation_order': i + 1
            })
            
            drafts.append(result)
            
            # Small delay to be respectful to the API
            import time
            time.sleep(0.5)
        
        logger.info(f"Generated {len(drafts)} visual drafts for {signal_type} signal on {symbol}")
        return drafts
    
    def save_drafts_locally(self, drafts: List[Dict[str, Any]], 
                          output_dir: str = "./visual_drafts") -> List[str]:
        """
        Save generated drafts to local files
        
        Args:
            drafts: List of draft results from generate_trading_visual_drafts
            output_dir: Directory to save draft images
            
        Returns:
            List of file paths where drafts were saved
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        saved_files = []
        
        for draft in drafts:
            if not draft.get('success', False):
                logger.warning(f"Skipping failed draft: {draft.get('error', 'Unknown error')}")
                continue
            
            # Generate filename
            signal_type = draft.get('signal_type', 'UNKNOWN')
            symbol = draft.get('symbol', 'CRYPTO')
            draft_id = draft.get('draft_id', 0)
            timestamp = int(__import__('time').time())
            
            filename = f"{symbol}_{signal_type}_draft{draft_id}_{timestamp}.png"
            filepath = output_path / filename
            
            # Save image data
            try:
                with open(filepath, 'wb') as f:
                    f.write(draft['image_data'])
                
                logger.info(f"Saved draft to {filepath}")
                saved_files.append(str(filepath))
                
            except Exception as e:
                logger.error(f"Failed to save draft {draft_id}: {e}")
        
        return saved_files

# Example usage
if __name__ == "__main__":
    # Initialize the drafting service
    drafter = PollinationsDrafting()
    
    # Example signal data
    example_signal = {
        'signal': 'BUY',
        'symbol': 'ETH',
        'confidence': 0.85,
        'reason': 'Volume spike with price breakout above resistance',
        'timestamp': '2026-05-07T10:30:00Z'
    }
    
    # Generate visual drafts
    print("Generating visual drafts for trading signal...")
    drafts = drafter.generate_trading_visual_drafts(example_signal, num_drafts=3)
    
    # Save drafts locally
    saved_files = drafter.save_drafts_locally(drafts, "./example_drafts")
    
    print(f"\nGenerated {len([d for d in drafts if d.get('success')])} successful drafts")
    print(f"Saved {len(saved_files)} draft files to ./example_drafts/")
    
    for i, draft in enumerate(drafts):
        if draft.get('success'):
            print(f"Draft {i+1}: SUCCESS - {draft.get('signal_type')} {draft.get('symbol')}")
        else:
            print(f"Draft {i+1}: FAILED - {draft.get('error')}")