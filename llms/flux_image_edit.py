import os
import base64
import time
import json
import binascii
import requests
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, Union
from dotenv import load_dotenv

from agent_graph.logger import (
    log_info, log_warning, log_error, log_success, log_debug,
    log_panel, log_loading, log_request_response, log_system
)

load_dotenv()


def edit_image_with_bfl(
    image_filepath: Union[str, Path],
    prompt: str,
    api_key: str,
    output_filename: Optional[str] = None
) -> Optional[str]:
    """
    Edit an image using Black Forest Labs API based on a text prompt.
    
    Args:
        image_filepath: Full path to the image file
        prompt: Text prompt describing the desired edits
        api_key: Your Black Forest Labs API key
        output_filename: Custom output filename. If None, auto-generates based on input
    
    Returns:
        Relative path from base directory (e.g., "images/edit_images/results/image.png"),
        or None if failed
        
    Raises:
        FileNotFoundError: If the input image doesn't exist
        ValueError: If the API request fails or returns an unexpected response
        requests.exceptions.RequestException: For network-related errors
    """
    start_time = time.time()
    log_info("Starting Flux image editing process")
    log_debug(f"Input image: {image_filepath}")
    log_debug(f"Prompt: {prompt}")
    
    # Set up paths
    output_dir = Path("images/edit_images/results")
    
    try:
        # Create output directory if it doesn't exist
        output_dir.mkdir(parents=True, exist_ok=True)
        log_debug(f"Output directory: {output_dir.absolute()}")
        
        # Full path to input image
        input_path = Path(image_filepath)
        
        # Check if input image exists
        if not input_path.exists():
            error_msg = f"Input image not found: {input_path}"
            log_error(error_msg)
            raise FileNotFoundError(error_msg)
        
        log_info(f"Processing image: {input_path.name} (Size: {input_path.stat().st_size / 1024:.2f} KB)")
        
        # Load and encode the image
        try:
            with open(input_path, "rb") as img_file:
                img_data = img_file.read()
                img_base64 = base64.b64encode(img_data).decode('utf-8')
            log_debug("Successfully encoded image to base64")
        except (IOError, OSError) as e:
            error_msg = f"Failed to read or encode image: {str(e)}"
            log_error(error_msg, exception=e)
            raise
        
        # Prepare the API request
        url = "https://api.bfl.ai/v1/flux-kontext-pro"
        
        headers = {
            "accept": "application/json",
            "x-key": api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "prompt": prompt,
            "input_image": img_base64,
            "width": 1024,
            "height": 1024,
            "steps": 50,
            "guidance_scale": 7.5,
            "seed": None
        }
        
        # Log the API request
        log_request_response(
            prompt,
            json.dumps({
                "image_size": f"{len(img_data) / 1024:.2f} KB",
                "width": 1024,
                "height": 1024,
                "steps": 50,
                "guidance_scale": 7.5
            }, indent=2)
        )
        
        log_info("Sending request to Flux Kontext Pro API...")
        
        # Make the API request
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=120)
            response.raise_for_status()
            log_success("Successfully received response from Flux Kontext Pro API")
            
            result = response.json()
            log_debug(f"API response: {json.dumps(result, indent=2) if len(str(result)) < 500 else 'Response too large to log'}")
            
            # Check if the response contains the edited image
            if 'images' in result and len(result['images']) > 0:
                log_debug("Processing direct image response")
                
                try:
                    # Decode the base64 image
                    edited_image_data = base64.b64decode(result['images'][0])
                    
                    # Generate output filename if not provided
                    if output_filename is None:
                        name_part = input_path.stem
                        extension = input_path.suffix or '.png'
                        timestamp = int(time.time())
                        output_filename = f"flux_edit_{name_part}_{timestamp}{extension}"
                    
                    # Save the edited image
                    output_path = output_dir / output_filename
                    
                    with open(output_path, "wb") as f:
                        f.write(edited_image_data)
                    
                    file_size = output_path.stat().st_size / 1024
                    log_success(f"Saved edited image to: {output_path} ({file_size:.2f} KB)")
                    
                    return f"images/edit_images/results/{output_filename}"
                    
                except (binascii.Error, IOError) as e:
                    error_msg = f"Failed to process or save image: {str(e)}"
                    log_error(error_msg, exception=e)
                    raise ValueError(error_msg) from e
            
            elif 'id' in result:
                # If the API returns a job ID (async processing)
                job_id = result['id']
                log_info(f"Image editing job submitted with ID: {job_id}")
                
                # Poll for results
                return poll_for_result(
                    job_id, 
                    api_key, 
                    output_dir, 
                    output_filename or f"flux_edit_{input_path.stem}_{int(time.time())}{input_path.suffix or '.png'}"
                )
            
            else:
                error_msg = f"Unexpected response format from API: {result}"
                log_error(error_msg)
                raise ValueError(error_msg)
                
        except requests.exceptions.RequestException as e:
            error_msg = f"API request failed: {str(e)}"
            log_error(error_msg, exception=e)
            if hasattr(e, 'response') and e.response is not None:
                log_error(f"Response status: {e.response.status_code}")
                try:
                    log_error(f"Response body: {e.response.text}")
                except Exception:
                    pass
            raise ValueError(error_msg) from e
            
    except Exception as e:
        error_msg = f"Error in edit_image_with_bfl: {str(e)}"
        log_error(error_msg, exception=e)
        raise

def poll_for_result(
    job_id: str,
    api_key: str,
    output_dir: Path,
    output_filename: str,
    max_wait: int = 600,
    poll_interval: int = 10
) -> Optional[str]:
    """
    Poll the BFL API for job completion and download the result.
    
    Args:
        job_id: The job ID returned by the API
        api_key: Your Black Forest Labs API key
        output_dir: Directory to save the result
        output_filename: Filename for the output
        max_wait: Maximum time to wait in seconds (default: 600s = 10 minutes)
        poll_interval: Time to wait between polls in seconds (default: 10s)
    
    Returns:
        Relative path from base directory, or None if failed
        
    Raises:
        TimeoutError: If the job doesn't complete within max_wait
        ValueError: If the job fails or returns an unexpected response
    """
    url = "https://api.bfl.ai/v1/get_result"
    headers = {
        "accept": "application/json",
        "x-key": api_key,
    }
    
    start_time = time.time()
    last_log_time = 0
    
    log_info(f"Starting to poll for job completion (timeout: {max_wait}s)")
    
    while time.time() - start_time < max_wait:
        current_time = time.time()
        
        # Log progress every 30 seconds
        if current_time - last_log_time >= 30:
            elapsed = int(current_time - start_time)
            log_info(f"Still waiting for job completion... (elapsed: {elapsed}s)")
            last_log_time = current_time
        
        try:
            # Make the API request with timeout
            response = requests.get(
                f"{url}?id={job_id}",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                status = result.get('status')
                
                log_debug(f"Job status: {status}")
                
                if status == 'Ready':
                    # Download the image
                    if 'result' in result and 'sample' in result['result']:
                        image_url = result['result']['sample']
                        log_info(f"Job completed, downloading image from: {image_url}")
                        
                        try:
                            # Download the image with timeout
                            img_response = requests.get(image_url, timeout=60)
                            img_response.raise_for_status()
                            
                            output_path = output_dir / output_filename
                            
                            with open(output_path, "wb") as f:
                                f.write(img_response.content)
                            
                            file_size = output_path.stat().st_size / 1024
                            log_success(f"Downloaded and saved image to: {output_path} ({file_size:.2f} KB)")
                            
                            return f"images/edit_images/results/{output_filename}"
                            
                        except requests.exceptions.RequestException as e:
                            error_msg = f"Failed to download image: {str(e)}"
                            log_error(error_msg, exception=e)
                            raise ValueError(error_msg) from e
                    
                elif status == 'Pending':
                    log_debug("Job still processing, waiting...")
                    time.sleep(poll_interval)
                    continue
                    
                else:
                    error_msg = f"Job failed with status: {status}"
                    log_error(error_msg)
                    log_debug(f"Full response: {json.dumps(result, indent=2)}")
                    raise ValueError(error_msg)
            
            else:
                error_msg = f"Failed to check job status: {response.status_code}"
                log_error(error_msg)
                log_debug(f"Response: {response.text}")
                time.sleep(poll_interval)
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Error checking job status: {str(e)}"
            log_error(error_msg, exception=e)
            time.sleep(poll_interval)
        
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse JSON response: {str(e)}"
            log_error(error_msg, exception=e)
            time.sleep(poll_interval)
    
    error_msg = f"Timeout waiting for job completion after {max_wait} seconds"
    log_error(error_msg)
    raise TimeoutError(error_msg)


def flux_image_edit(prompt: str, image_path: str) -> Tuple[str, str]:
    """
    Edit an image using the Flux Kontext Pro API.
    
    Args:
        prompt: Text prompt describing the desired edits
        image_path: Path to the input image file
        
    Returns:
        Tuple containing (error_message, result_path)
        - If successful: ("", result_path)
        - If failed: (error_message, "")
    """
    start_time = time.time()
    log_info("Starting Flux image editing process")
    log_debug(f"Input image: {image_path}")
    log_debug(f"Prompt: {prompt}")
    
    # Get API key from environment
    api_key = os.getenv("BFL_API_KEY")
    if not api_key:
        error_msg = "BFL_API_KEY environment variable not set"
        log_error(error_msg)
        return error_msg, ""
    
    try:
        # Edit the image
        result = edit_image_with_bfl(
            image_filepath=image_path,
            prompt=prompt,
            api_key=api_key
        )
        
        if result:
            log_success(f"Successfully edited image: {result}")
            log_info(f"Total processing time: {time.time() - start_time:.2f} seconds")
            return "", result
        else:
            error_msg = "Image editing failed: No result returned"
            log_error(error_msg)
            return error_msg, ""
            
    except Exception as e:
        error_msg = f"Error in flux_image_edit: {str(e)}"
        log_error(error_msg, exception=e)
        return error_msg, ""


# Example usage
if __name__ == "__main__":
    # Set your API key
    API_KEY = str(os.getenv("BFL_API_KEY"))
    
    # Example: Edit a single image
    result = edit_image_with_bfl(
        image_filepath="images/edit_images/saved_images/dall_e_image_20250610_130858.png",
        prompt="Make the cat blue",
        api_key=API_KEY
    )
    
    if result:
        print(f"Edited image saved at: {result}")
    else:
        print("Image editing failed")