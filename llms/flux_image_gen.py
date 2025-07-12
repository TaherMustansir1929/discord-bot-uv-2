import requests
import json
import time
import base64
import binascii
import logging
from typing import Optional, Dict, Any, Tuple, Union
import os
from pathlib import Path
from datetime import datetime

from agent_graph.logger import (
    log_info, log_warning, log_error, log_success, log_debug,
    log_panel, log_loading, log_request_response, log_system
)

class FluxImageGenerator:
    def __init__(self, api_key: str, base_url: str = "https://api.a4f.co/v1"):
        """
        Initialize the Flux Image Generator
        
        Args:
            api_key: Your a4f.co API key
            base_url: Base URL for the API (default: https://api.a4f.co/v1)
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        log_debug(f"Initialized FluxImageGenerator with base URL: {self.base_url}")
    
    def generate_image(self, 
                      prompt: str,
                      model: str = "flux-pro",
                      width: int = 1024,
                      height: int = 1024,
                      steps: int = 25,
                      guidance_scale: float = 7.0,
                      seed: Optional[int] = None,
                      negative_prompt: Optional[str] = None,
                      output_format: str = "png") -> Dict[str, Any]:
        """
        Generate an image using Flux models
        
        Args:
            prompt: Text description of the image to generate
            model: Model to use (flux-pro, flux-dev, flux-schnell)
            width: Image width in pixels
            height: Image height in pixels
            steps: Number of inference steps
            guidance_scale: How closely to follow the prompt
            seed: Random seed for reproducibility
            negative_prompt: What to avoid in the image
            output_format: Output format (png, jpg, webp)
            
        Returns:
            Dictionary containing the response data or error information
            
        Raises:
            requests.exceptions.RequestException: If the API request fails
            ValueError: If the response cannot be parsed as JSON
        """
        start_time = time.time()
        log_info(f"Generating image with model: {model}")
        log_debug(f"Prompt: {prompt}")
        log_debug(f"Dimensions: {width}x{height}, Steps: {steps}, Guidance: {guidance_scale}")
        
        payload = {
            "prompt": prompt,
            "model": model,
            "width": width,
            "height": height,
            "steps": steps,
            "guidance_scale": guidance_scale,
            "output_format": output_format
        }
        
        if seed is not None:
            payload["seed"] = seed
            log_debug(f"Using fixed seed: {seed}")
            
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
            log_debug(f"Negative prompt: {negative_prompt}")
        
        # Log the API request
        log_request_response(
            prompt,
            str({
                "model": model,
                "width": width,
                "height": height,
                "steps": steps,
                "guidance_scale": guidance_scale,
                "output_format": output_format,
                "has_seed": seed is not None,
                "has_negative_prompt": bool(negative_prompt)
            })
        )
        
        try:
            log_info("Sending request to Flux API...")
            response = requests.post(
                f"{self.base_url}/images/generations",
                headers=self.headers,
                json=payload,
                timeout=120
            )
            response.raise_for_status()
            log_success("Successfully received response from Flux API")
            
            # Log response time
            api_time = time.time() - start_time
            log_debug(f"API response time: {api_time:.2f} seconds")
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Flux API request failed: {str(e)}"
            log_error(error_msg, exception=e)
            return {"error": error_msg}
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse JSON response: {str(e)}"
            log_error(error_msg, exception=e)
            return {"error": error_msg}
    
    def save_image_from_response(self, 
                              response_data: Dict[str, Any], 
                              filename: Optional[str] = None,
                              output_dir: Union[str, Path] = "images/generated_images") -> str:
        """
        Save image from API response to file
        
        Args:
            response_data: Response from generate_image()
            filename: Custom filename (optional)
            output_dir: Directory to save images
            
        Returns:
            Path to saved image file
            
        Raises:
            ValueError: If there's an error in the response or saving fails
            IOError: If there's an error writing the file
        """
        log_info("Saving image from API response")
        
        if "error" in response_data:
            error_msg = f"Cannot save image due to error: {response_data['error']}"
            log_error(error_msg)
            raise ValueError(error_msg)
        
        try:
            # Create output directory if it doesn't exist
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            log_debug(f"Output directory: {output_dir.absolute()}")
            
            # Generate filename if not provided
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"flux_image_{timestamp}.png"
            
            filepath = output_dir / filename
            
            # Handle different response formats
            if not response_data.get("data") or not isinstance(response_data["data"], list):
                error_msg = "Invalid response format: missing or empty 'data' field"
                log_error(error_msg)
                raise ValueError(error_msg)
                
            image_data = response_data["data"][0]
            
            if "b64_json" in image_data:
                # Base64 encoded image
                log_debug("Processing base64 encoded image")
                try:
                    image_bytes = base64.b64decode(image_data["b64_json"])
                    with open(filepath, "wb") as f:
                        f.write(image_bytes)
                    log_success(f"Saved base64 encoded image to: {filepath}")
                    log_debug(f"File size: {filepath.stat().st_size / 1024:.2f} KB")
                except (binascii.Error, IOError) as e:
                    error_msg = f"Failed to decode or save base64 image: {str(e)}"
                    log_error(error_msg, exception=e)
                    raise IOError(error_msg)
                    
            elif "url" in image_data:
                # Image URL - download it
                log_debug(f"Downloading image from URL: {image_data['url']}")
                try:
                    img_response = requests.get(image_data["url"], timeout=30)
                    img_response.raise_for_status()
                    with open(filepath, "wb") as f:
                        f.write(img_response.content)
                    log_success(f"Downloaded and saved image to: {filepath}")
                    log_debug(f"File size: {filepath.stat().st_size / 1024:.2f} KB")
                except requests.exceptions.RequestException as e:
                    error_msg = f"Failed to download image from URL: {str(e)}"
                    log_error(error_msg, exception=e)
                    raise IOError(error_msg)
            else:
                error_msg = "No valid image data found in response (missing b64_json or url)"
                log_error(error_msg)
                log_debug(f"Response data: {json.dumps(response_data, indent=2)}")
                raise ValueError(error_msg)
            
            return str(filepath)
            
        except Exception as e:
            error_msg = f"Unexpected error saving image: {str(e)}"
            log_error(error_msg, exception=e)
            raise
    
    def generate_and_save(self, 
                         prompt: str,
                         filename: Optional[str] = None,
                         **kwargs) -> Tuple[str, str]:
        """
        Generate an image and save it in one step
        
        Args:
            prompt: Text description of the image
            filename: Custom filename (optional)
            **kwargs: Additional arguments for generate_image()
            
        Returns:
            Tuple containing (filepath, ai_response)
            
        Raises:
            ValueError: If image generation or saving fails
        """
        start_time = time.time()
        log_info("Starting image generation and save process")
        log_debug(f"Prompt: {prompt}")
        log_debug(f"Additional kwargs: {kwargs}")
        
        try:
            # Generate the image
            response = self.generate_image(prompt, **kwargs)
            
            if "error" in response:
                error_msg = f"Image generation failed: {response['error']}"
                log_error(error_msg)
                raise ValueError(error_msg)
            
            # Save the image
            filepath = self.save_image_from_response(response, filename)
            
            # Extract AI response or generate a default one
            ai_response = response.get("data", [{}])[0].get("revised_prompt")
            if ai_response is None:
                ai_response = f"Generated image successfully for prompt: {prompt}"
                log_debug("No revised prompt in response, using default")
            else:
                log_debug(f"Received revised prompt from API: {ai_response}")
            
            # Log success
            total_time = time.time() - start_time
            log_success(f"Image generation and save completed in {total_time:.2f} seconds")
            log_info(f"Image saved to: {filepath}")
            
            return filepath, ai_response
            
        except Exception as e:
            error_msg = f"Error in generate_and_save: {str(e)}"
            log_error(error_msg, exception=e)
            raise ValueError(error_msg) from e

def flux_image_generator(prompt: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Generate an image using Flux API based on the given prompt.
    
    Args:
        prompt: Text description of the desired image
        
    Returns:
        Tuple containing (ai_response, filepath) or (None, None) on failure
    """
    log_info("Starting Flux image generation")
    log_debug(f"Input prompt: {prompt}")
    
    # Initialize the generator with API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        error_msg = "OPENAI_API_KEY environment variable not set"
        log_error(error_msg)
        return None, None
        
    try:
        generator = FluxImageGenerator(api_key)
        log_debug("Initialized FluxImageGenerator")
        
        # Generate and save the image
        filepath, response = generator.generate_and_save(
            prompt=prompt,
            model="provider-1/FLUX.1.1-pro",
            width=1024,
            height=1024,
            steps=30,
            guidance_scale=7.5,
            seed=42  # For reproducible results
        )
        
        log_success(f"Image generation completed successfully")
        log_info(f"Image saved to: {filepath}")
        log_debug(f"AI response: {response}")
        
        return response, filepath
        
    except Exception as e:
        error_msg = f"Failed to generate image: {str(e)}"
        log_error(error_msg, exception=e)
        return None, None
    
    # # Example 2: Generate multiple variations
    # prompts = [
    #     "A cyberpunk cityscape at night with neon lights",
    #     "A serene forest landscape with morning mist",
    #     "A vintage car on an empty desert highway"
    # ]
    
    # for i, prompt in enumerate(prompts):
    #     try:
    #         filepath = generator.generate_and_save(
    #             prompt=prompt,
    #             filename=f"variation_{i+1}.png",
    #             model="flux-pro",
    #             width=1024,
    #             height=768,
    #             steps=25
    #         )
    #         print(f"Generated variation {i+1}: {filepath}")
            
    #     except Exception as e:
    #         print(f"Failed to generate variation {i+1}: {e}")

if __name__ == "__main__":
    flux_image_generator("A majestic dragon soaring through cloudy skies at sunset, photorealistic, highly detailed")