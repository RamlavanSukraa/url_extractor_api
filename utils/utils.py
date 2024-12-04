# utils.py
import io
import os
import socket
import requests
import base64
import httpx
from datetime import datetime
from PIL import Image, ImageOps
from fastapi import HTTPException
from utils.logger import app_logger


# Configure logger
logger = app_logger



valid_extensions = ['png', 'jpg', 'jpeg', 'gif', 'webp']

def is_running_in_docker():
    """Check if the code is running inside a Docker container."""
    try:
        with open('/proc/self/cgroup', 'r') as f:
            return any('docker' in line for line in f)
    except FileNotFoundError:
        return False

def resolve_host_ip():
    """Resolve the appropriate IP to use if the app is running inside Docker."""
    if is_running_in_docker():
        try:
            # Attempt to resolve 'host.docker.internal' for Docker compatibility
            return socket.gethostbyname('host.docker.internal')
        except socket.gaierror:
            # Fallback to loopback IP if 'host.docker.internal' is unavailable
            return '127.0.0.1'
    return None  # Not in Docker, use provided hostname as-is

def load_image_from_source(source_path: str):
    """
    Load an image from an external URL or local path.
    Handles special cases for localhost when running inside Docker.
    """
    try:
        if source_path.startswith("http://") or source_path.startswith("https://"):
            # Adjust URL if it's localhost and running inside Docker
            if 'localhost' in source_path or '127.0.0.1' in source_path:
                resolved_ip = resolve_host_ip()
                if resolved_ip:
                    source_path = source_path.replace('localhost', resolved_ip).replace('127.0.0.1', resolved_ip)

            response = requests.get(source_path)
            response.raise_for_status()
            img = Image.open(io.BytesIO(response.content))
        else:
            # Handle local file paths
            if not os.path.exists(source_path):
                raise FileNotFoundError(f"File not found: {source_path}")
            img = Image.open(source_path)

        return img
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Error loading image from URL: {e}")
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading image: {e}")

def validate_image(image):
    try:
        logger.info("Validating image format.")
        img = Image.open(image)
        img.verify()  # Verify that it is an image
        if img.format.lower() not in valid_extensions:
            logger.warning(f"Unsupported image format: {img.format}")
            raise ValueError(f"Unsupported image format: {img.format}")
        logger.info("Image validation successful.")
    except Exception as e:
        logger.error(f"Image validation failed: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid image: {e}")
    finally:
        if hasattr(image, 'seek'):
            image.seek(0)  # Reset file pointer after verification

def encode_image(image_bytes: bytes):
    try:
        logger.info("Encoding image to Base64.")
        encoded_image = base64.b64encode(image_bytes).decode("utf-8")
        logger.info("Image encoding complete.")
        return encoded_image
    except Exception as e:
        logger.error(f"Error encoding image: {e}")
        raise HTTPException(status_code=500, detail=f"Error encoding image: {e}")

def compress_image(image, max_size_mb: float):
    try:
        logger.info(f"Compressing image to ensure it is less than {max_size_mb} MB.")
        img = Image.open(image)
        img_format = img.format  # Get the original format

        quality = 95
        buffer = io.BytesIO()

        # Ensure the output directory exists
        if not os.path.exists('output'):
            os.makedirs('output')
            logger.info("Created 'output' directory for compressed images.")

        while True:
            buffer.seek(0)
            img.save(buffer, format=img_format, quality=quality)
            size_kb = buffer.tell() / 1024
            logger.debug(f"Current compressed size: {size_kb:.2f} KB with quality: {quality}")
            if size_kb <= max_size_mb * 1024 or quality <= 5:
                break  # Stop if the image is within size or quality is too low

            quality -= 5

        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        compressed_image_name = f"compressed_image_{timestamp}.{img_format.lower()}"
        compressed_image_path = os.path.join('output', compressed_image_name)

        with open(compressed_image_path, 'wb') as f:
            f.write(buffer.getvalue())

        logger.info(f"Image compression complete. Saved at: {compressed_image_path}")
        return compressed_image_path

    except Exception as e:
        logger.error(f"Error compressing image: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error compressing image: {e}")
    finally:
        if hasattr(image, 'seek'):
            image.seek(0)  # Reset file pointer after compression




def to_empty_string(value):
    return value if value is not None else ""

