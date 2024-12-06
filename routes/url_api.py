# routes/url_api.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx
from datetime import datetime
from fastapi.responses import JSONResponse

# import utils
from utils.img_operations import load_image_from_url, validate_image, compress_image, encode_image
from utils.logger import app_logger

# Initialize the logger
logger = app_logger

router = APIRouter()

class InputData(BaseModel):
    url: str
    booking_id: str

@router.post("/api/v1/ExtractData")
async def extract_url(request: InputData):
    try:
        logger.info(f"Processing request from URL: {request.url}")

        # Step 1: Load the image from the provided URL
        image = load_image_from_url(request.url)
        logger.info(f"Image successfully loaded. Format: {image.format}")

        # Step 2: Validate the image format
        validate_image(image, request.url)
        logger.info("Image validation successful.")

        # Step 3: Compress the image to reduce image size
        compressed_image_path = compress_image(image, max_size_mb=0.5)
        logger.info(f"Image compressed successfully. Path: {compressed_image_path}")

        # Step 4: Encode the image (if required by API)
        with open(compressed_image_path, "rb") as f:
            encoded_image = encode_image(f.read())
        logger.info("Image encoded successfully.")

        # Step 5: Send the compressed image to the AI engine
        logger.info("Sending the image for data extraction.")
        with open(compressed_image_path, "rb") as image_file:
            async with httpx.AsyncClient(follow_redirects=True, timeout=120.0) as client:
                try:
                    response = await client.post(
                        "http://51.20.150.57:5006/extract_and_map_tests/",
                        files={"file": ("image", image_file)}
                    )
                    response.raise_for_status()  # Raise detailed exceptions for HTTP errors
                except httpx.RequestError as e:
                    logger.error(f"Error communicating with the extraction API: {e}")
                    raise HTTPException(status_code=500, detail=f"Connection error: {e}")

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Extraction API error: {response.text}",
            )

        # Step 6: Process the API response
        response_data = response.json()
        response_data.pop('base64', None)  # Remove unnecessary 'base64' key if present
        logger.info("Extraction process completed successfully.")

        # Step 7: Prepare payload for MongoDB insertion
        extracted_data = response_data.get("extracted_data", {})
        mapped_tests = response_data.get("mapped_tests", [])
        extracted_data_AI = {
            # Extract relevant fields and handle None values
            "doc_date": str(extracted_data.get("date", "") or ""),
            "pt_address": str(extracted_data.get("patient_address", "") or ""),
            "pt_age": str(extracted_data.get("patient_age", "") or ""),
            "pt_age_period": str(extracted_data.get("patient_age_period", "") or ""),
            "pt_contact": str(extracted_data.get("patient_contact", "") or ""),
            "pt_name": str(extracted_data.get("patient_name", "") or ""),
            "pt_sex": str(extracted_data.get("patient_sex", "") or ""),
            "pt_title": str(extracted_data.get("patient_title", "") or ""),
            "ref_name": str(extracted_data.get("referrer_name", "") or ""),
            "ref_type": str(extracted_data.get("referrer_type", "") or ""),
            "mapped_ref_name": str(extracted_data.get("matched_ref_name", "") or ""),
            "mapped_ref_type": str(extracted_data.get("matched_ref_type", "") or ""),
            "mapped_ref_code": str(extracted_data.get("matched_ref_code", "") or ""),
            "remark": str(extracted_data.get("remark", "") or ""),
            "uhid_id": str(extracted_data.get("ID", "") or ""),
            "prescribed_tests": [
                {
                    "extracted_test_name": str(mt.get("input_test_name", "") or ""),
                    "mapped_test_name": str(mt.get("matched_test_name", "") or ""),
                    "mapped_test_code": str(mt.get("matched_test_code", "") or ""),
                } for mt in mapped_tests
            ]
        }
        payload = {
            "extracted_data_AI": extracted_data_AI,
            "created_by": {"userId": "user_id", "CRNID": "crn_id"},
            "created_at": datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),
            "booking_id": request.booking_id,
        }

        # Step 8: Insert the payload into MongoDB via external API
        db_api_url = "http://51.20.150.57:5009/api/v1/prescriptions"
        logger.info(f"Sending payload to MongoDB API: {db_api_url}")
        async with httpx.AsyncClient() as client:
            try:
                db_api_response = await client.post(db_api_url, json=payload, timeout=120)
            except httpx.RequestError as e:
                logger.error(f"External API communication error: {e}")
                raise HTTPException(status_code=500, detail=f"External API error: {str(e)}")
        
        # Handle MongoDB API response
        if db_api_response.status_code in [200, 201]:
            response_data = db_api_response.json()
            
            # Ensure `_id` is properly formatted
            if '_id' in response_data:
                response_data['_id'] = str(response_data['_id']).replace("ObjectId(", "").replace(")", "").strip()
                logger.info(f"Formatted MongoDB _id: {response_data['_id']}")

            # Ensure the `booking_id` is correctly included in the response
            response_data['booking_id'] = payload.get('booking_id', 'N/A')
            logger.info("Data saved to MongoDB successfully.")
            return response_data

        else:
            logger.error(f"MongoDB API error: {db_api_response.status_code} - {db_api_response.text}")
            raise HTTPException(
                status_code=db_api_response.status_code,
                detail=f"MongoDB API error: {db_api_response.text}",
            )

    except HTTPException as http_exc:
        logger.error(f"HTTPException occurred: {http_exc.detail}")
        return JSONResponse(status_code=http_exc.status_code, content={"error": http_exc.detail})
    except Exception as exc:
        logger.error(f"Unexpected error occurred: {str(exc)}")
        return JSONResponse(status_code=500, content={"error": "Internal Server Error"})
