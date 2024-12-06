# utils/img_operations.py

from fastapi import HTTPException, UploadFile
from PIL import Image
import base64
import io
import os
from datetime import datetime
import requests
from urllib.parse import urlparse
from utils.logger import    app_logger



# Valid image extensions
valid_extensions = ['png', 'jpg', 'jpeg', 'gif', 'webp']


def load_image_from_url(source_path: str) -> Image.Image:
    """
    Load an image from a URL without validation.
    """
    try:
        # Validate the URL starts with HTTP or HTTPS
        if not source_path.startswith(("http://", "https://")):
            raise HTTPException(status_code=400, detail="Source path must be an HTTP or HTTPS URL.")

        # Fetch the image content
        response = requests.get(source_path, timeout=10)
        response.raise_for_status()  # Raise exception for HTTP errors

        # Open the image using PIL
        img = Image.open(io.BytesIO(response.content))
        return img

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Error loading image from URL: {e}")
    except (Image.UnidentifiedImageError, IOError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid or corrupted image: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error while loading image: {e}")





def validate_image(image: UploadFile | Image.Image, source_path: str = None) -> Image.Image:
    """
    Validate an image, ensure it has a supported format, and optionally attach the original filename.
    Handles both UploadFile (from FastAPI) and Image.Image (from PIL).
    """
    try:
        # Read image data based on input type
        if isinstance(image, UploadFile):
            app_logger.info("Reading image from UploadFile.")
            content = image.file.read()
            pil_image = Image.open(io.BytesIO(content))
        elif isinstance(image, Image.Image):
            app_logger.info("Processing existing PIL Image.")
            buffer = io.BytesIO()
            image.save(buffer, format=image.format)  # Save the image to a buffer
            buffer.seek(0)
            pil_image = Image.open(buffer)  # Reopen the image from the buffer
        else:
            raise ValueError("Unsupported image input type. Expected UploadFile or Image.Image.")

        # Verify the image's integrity
        app_logger.info("Verifying image integrity.")
        pil_image.verify()  # This invalidates the image instance

        # Reopen the image using original content after verification
        app_logger.info("Reopening image after verification.")
        if isinstance(image, UploadFile):
            pil_image = Image.open(io.BytesIO(content))
        else:
            buffer.seek(0)
            pil_image = Image.open(buffer)

        # Validate the image format
        app_logger.info(f"Validating image format: {pil_image.format}")
        if pil_image.format.lower() not in valid_extensions:
            raise ValueError(f"Unsupported image format: {pil_image.format}")

        # Extract and assign filename
        if source_path:
            parsed_url = urlparse(source_path)
            pil_image.filename = os.path.basename(parsed_url.path)
        elif isinstance(image, UploadFile):
            pil_image.filename = image.filename

        app_logger.info(f"Validation complete. Image filename: {pil_image.filename}")
        return pil_image

    except Exception as e:
        app_logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid image: {e}")

    finally:
        if isinstance(image, UploadFile):
            image.file.seek(0)  # Reset file pointer for UploadFile







def encode_image(image_bytes: bytes):
    try:
        encoded_image = base64.b64encode(image_bytes).decode("utf-8")
        return encoded_image
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error encoding image: {e}")
    

def compress_image(image: UploadFile | Image.Image, max_size_mb: 0.5) -> str:
    """
    Compress an image to ensure it is within the specified max size in MB.
    Supports both UploadFile and PIL.Image.Image.
    """
    try:
        # Determine the input type and open the image accordingly
        if isinstance(image, UploadFile):
            img = Image.open(image.file)
            img_format = img.format
        elif isinstance(image, Image.Image):
            img = image
            img_format = img.format
        else:
            raise ValueError("Unsupported image input type. Expected UploadFile or Image.Image.")

        # Set initial quality and create a buffer to hold the compressed image
        quality = 95
        buffer = io.BytesIO()

        while True:
            # Seek to the start of the buffer
            buffer.seek(0)
            # Save image to buffer with current quality settings
            img.save(buffer, format=img_format, quality=quality)
            # Check the size of the buffer in kilobytes
            size_kb = buffer.tell() / 1024
            if size_kb <= max_size_mb * 1024 or quality <= 5:
                break  # Stop if the image is within size or quality is too low

            # Reduce the quality for further compression
            quality -= 5

        # Ensure the output directory exists
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)

        # Generate output path and save the compressed image
        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        base_name = os.path.splitext(image.filename if isinstance(image, UploadFile) else img.filename)[0]
        compressed_image_name = f"{base_name}_{timestamp}.{img_format.lower()}"
        compressed_image_path = os.path.join(output_dir, compressed_image_name)

        # Write buffer content to the output file
        with open(compressed_image_path, 'wb') as f:
            f.write(buffer.getvalue())

        return compressed_image_path

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error compressing image: {e}")

    finally:
        if isinstance(image, UploadFile):
            image.file.seek(0)  # Reset file pointer after compression
