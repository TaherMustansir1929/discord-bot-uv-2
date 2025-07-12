from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
from datetime import datetime
import os
import time
import traceback
from pathlib import Path
from typing import Tuple, Optional

from agent_graph.logger import (
    log_info, log_warning, log_error, log_success, log_debug,
    log_panel, log_loading, log_request_response, log_system
)
from my_prompts.image_edit import image_edit_prompt


def gemini_image_gen(user_prompt: str) -> Tuple[str, str]:
    """
    Generate an image using Gemini's image generation model.
    
    Args:
        user_prompt: The text prompt for image generation
        
    Returns:
        Tuple containing (generated_text, output_image_path)
    """
    start_time = time.time()
    log_info("Starting Gemini image generation")
    log_debug(f"User prompt: {user_prompt}")
    
    try:
        client = genai.Client()
        log_debug("Initialized Gemini client")

        contents = f"""
        System: Generate an image that closely adheres to the provided description, focusing on realism, accuracy, and lifelike details. Avoid fantastical or whimsical elements unless explicitly requested. Interpret the description with precision and creativity. Even if the prompt is vague, surreal, inappropriate or unconventional, always generate a visual response—use imaginative judgment to ensure the result is to-the-point, coherent and realistic visual interpretation. Never skip generation.

        User: {user_prompt}
        """
        log_debug("Prepared generation prompt")

        # Log the API request
        log_request_response(
            user_prompt,
            str({
                "model": "gemini-2.0-flash-preview-image-generation"
            })
        )

        # Make the API call with error handling
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash-preview-image-generation",
                contents=contents,
                config=types.GenerateContentConfig(
                    response_modalities=['TEXT', 'IMAGE']
                )
            )
            log_success("Successfully received response from Gemini API")
        except Exception as api_error:
            error_msg = f"Gemini API error: {str(api_error)}"
            log_error(error_msg, exception=api_error)
            raise RuntimeError("Failed to generate image. Please try again later.")

        # Create output directory
        image_folder = "images/generated_images"
        os.makedirs(image_folder, exist_ok=True)
        log_debug(f"Output directory: {os.path.abspath(image_folder)}")

        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"gemini_image_{timestamp}.png"
        output_path = os.path.join(image_folder, filename)
        
        log_info(f"Saving generated image to: {output_path}")

        # Process response
        message = ""
        image_saved = False
        
        if not hasattr(response, 'candidates') or not response.candidates:
            error_msg = "No candidates in API response"
            log_error(error_msg)
            raise ValueError("Invalid response from image generation service")

        for part in response.candidates[0].content.parts:  # type: ignore
            try:
                if part.text is not None:
                    message = str(part.text)
                    log_debug(f"Received text response: {message[:100]}..." if len(message) > 100 else message)
                elif hasattr(part, 'inline_data') and part.inline_data is not None:
                    image = Image.open(BytesIO(part.inline_data.data))  # type: ignore
                    image.save(output_path)
                    image_saved = True
                    log_success(f"Image saved successfully: {output_path}")
                    log_debug(f"Image size: {os.path.getsize(output_path) / 1024:.2f} KB")
            except Exception as part_error:
                error_msg = f"Error processing response part: {str(part_error)}"
                log_error(error_msg, exception=part_error)
                continue

        if not image_saved:
            error_msg = "No valid image data found in the response"
            log_error(error_msg)
            raise ValueError("Failed to generate image. Please try again with a different prompt.")

        execution_time = time.time() - start_time
        log_success(f"Image generation completed in {execution_time:.2f} seconds")
        
        return message, output_path
        
    except Exception as e:
        error_msg = f"Error in gemini_image_gen: {str(e)}"
        log_error(error_msg, exception=e)
        raise


def gemini_image_edit(user_prompt: str, image_path: str) -> Tuple[str, str]:
    """
    Edit an image using Gemini's image editing capabilities.
    
    Args:
        user_prompt: The text prompt for image editing
        image_path: Path to the input image to be edited
        
    Returns:
        Tuple containing (generated_text, output_image_path)
    """
    start_time = time.time()
    log_info("Starting Gemini image editing")
    log_debug(f"User prompt: {user_prompt}")
    log_debug(f"Input image: {image_path}")
    
    try:
        # Validate input image
        if not os.path.exists(image_path):
            error_msg = f"Input image not found: {image_path}"
            log_error(error_msg)
            raise FileNotFoundError(error_msg)
            
        try:
            image = Image.open(image_path)
            log_debug(f"Loaded input image: {image_path} (Size: {os.path.getsize(image_path) / 1024:.2f} KB)")
        except Exception as img_error:
            error_msg = f"Failed to load image: {str(img_error)}"
            log_error(error_msg, exception=img_error)
            raise ValueError("Invalid image file. Please provide a valid image.")

        # Initialize client
        client = genai.Client()
        log_debug("Initialized Gemini client")

        # Prepare the prompt
        text_input = f"""
        # SYSTEM PROMPT:
        {image_edit_prompt}

        # USER PROMPT:
        {user_prompt}
        """
        log_debug("Prepared editing prompt")

        # Log the API request
        log_request_response(
            user_prompt,
            str({
                "image_path": image_path,
                "image_size": f"{os.path.getsize(image_path) / 1024:.2f} KB",
                "model": "gemini-2.0-flash-preview-image-generation"
            })
        )

        # Make the API call with error handling
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash-preview-image-generation",
                contents=[text_input, image],
                config=types.GenerateContentConfig(
                    response_modalities=['TEXT', 'IMAGE']
                )
            )
            log_success("Successfully received response from Gemini API")
        except Exception as api_error:
            error_msg = f"Gemini API error: {str(api_error)}"
            log_error(error_msg, exception=api_error)
            raise RuntimeError("Failed to edit image. Please try again later.")

        # Create output directory
        image_folder = "images/edit_images/results"
        os.makedirs(image_folder, exist_ok=True)
        log_debug(f"Output directory: {os.path.abspath(image_folder)}")

        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"result_{timestamp}.png"
        output_path = os.path.join(image_folder, filename)
        
        log_info(f"Saving edited image to: {output_path}")

        # Process response
        message = ""
        image_saved = False
        
        if not hasattr(response, 'candidates') or not response.candidates:
            error_msg = "No candidates in API response"
            log_error(error_msg)
            raise ValueError("Invalid response from image editing service")

        for part in response.candidates[0].content.parts:  # type: ignore
            try:
                if part.text is not None:
                    message = str(part.text)
                    log_debug(f"Received text response: {message[:100]}..." if len(message) > 100 else message)
                elif hasattr(part, 'inline_data') and part.inline_data is not None:
                    edited_image = Image.open(BytesIO(part.inline_data.data))  # type: ignore
                    edited_image.save(output_path)
                    image_saved = True
                    log_success(f"Edited image saved successfully: {output_path}")
                    log_debug(f"Edited image size: {os.path.getsize(output_path) / 1024:.2f} KB")
            except Exception as part_error:
                error_msg = f"Error processing response part: {str(part_error)}"
                log_error(error_msg, exception=part_error)
                continue

        if not image_saved:
            error_msg = "No valid image data found in the response"
            log_error(error_msg)
            raise ValueError("Failed to edit image. Please try again with a different prompt.")

        execution_time = time.time() - start_time
        log_success(f"Image editing completed in {execution_time:.2f} seconds")
        
        return message, output_path
        
    except Exception as e:
        error_msg = f"Error in gemini_image_edit: {str(e)}"
        log_error(error_msg, exception=e)
        raise