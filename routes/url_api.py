import io
import json
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx

from openai import OpenAI  # Ensure correct import for OpenAI client library
from config import load_config, app_logger
from utils.testMap_utils import map_test_code, map_ref_code
from utils.utils import load_image_from_source, validate_image, encode_image, compress_image

# Setup logging config
logger = app_logger

# Load configuration values
config = load_config()
API_KEY = config['api_key']
MODEL = config['model']
MAX_SIZE_MB = config['max_size_mb']
threshold = config['threshold']

# Initialize OpenAI client globally
openai_client = OpenAI(api_key=API_KEY)

router = APIRouter()

# Pydantic model for input
class ImageURL(BaseModel):
    url: str
    booking_id: str  # Ensure the booking ID is passed by the user

@router.post("/extract_and_map_tests_url/")
async def extract_and_map_tests(image_url: ImageURL):
    """
    Extracts test names from an image given via an HTTP/HTTPS URL,
    maps them to test codes, and sends the result to an external API.
    The booking_id is provided by the user and is included in the payload.
    """
    try:
        logger.info(f"Received request for image processing from URL: {image_url.url}")

        # Step 1: Validate and load the image from the URL
        if image_url.url.startswith("http://") or image_url.url.startswith("https://"):
            image = load_image_from_source(image_url.url)
            logger.debug("Image successfully loaded from URL.")
        else:
            logger.error("Invalid URL format provided.")
            raise HTTPException(status_code=400, detail="Invalid URL format. Must be an HTTP/HTTPS URL.")

        # Step 2: Convert image to bytes and validate
        logger.info("Converting image to bytes and validating.")
        image_bytes = io.BytesIO()
        image.save(image_bytes, format=image.format)
        image_bytes.seek(0)
        validate_image(image_bytes)
        logger.info("Image validation complete.")

        # Step 3: Compress and encode the image
        logger.info("Compressing the image if needed.")
        compressed_image_path = compress_image(image_bytes, MAX_SIZE_MB)
        logger.info(f"Image compressed and saved at: {compressed_image_path}")

        logger.info("Encoding image to Base64.")
        with open(compressed_image_path, 'rb') as f:
            encoded_image = encode_image(f.read())
        logger.info("Image encoding complete.")

        # Step 4: Read the prompt template
        logger.info("Reading the prompt template for OpenAI request.")
        with open('prompt_template.txt', 'r') as prompt_file:
            prompt_template = prompt_file.read()

        # Step 5: Send the image and prompt to OpenAI's API
        logger.info("Sending the image to OpenAI API for test name extraction.")
        response = openai_client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that responds in JSON format. Extract patient data and prescribed lab tests from a medical prescription."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt_template
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"}
                        }
                    ]
                }
            ],
            temperature=0.0,
        )
        logger.info("OpenAI API call complete.")

        # Step 6: Parse the GPT response
        logger.debug("Parsing the response from OpenAI API.")
        gpt_response = response.choices[0].message.content.split('```json')[-1].split('```')[0]
        extracted_data = json.loads(gpt_response)
        logger.info("Parsed GPT response successfully.")




        # Replace 'UHID/ID' with 'ID' for consistency
        if "UHID/ID" in extracted_data:
            extracted_data['ID'] = extracted_data.pop("UHID/ID")

        # Set default values for all potentially missing fields
        fields_to_check = [
            "date", "patient_address", "patient_contact", "patient_age", "patient_age_period",
            "patient_name", "patient_sex", "patient_title", "referrer_name", "referrer_type",
            "matched_ref_name", "matched_ref_type", "matched_ref_code", "remark", "ID"
        ]

        for field in fields_to_check:
            extracted_data[field] = extracted_data.get(field, "") or ""

        # Ensure `pt_age` is a string
        extracted_data['patient_age'] = str(extracted_data['patient_age'])

        # Step 7: Extract test names and map them
        test_names = extracted_data.get("prescribed_test", [])
        mapped_tests = []
        for input_test_name in test_names:
            matched_test_name, matched_test_code = map_test_code(input_test_name, threshold)
            mapped_tests.append({
                "extracted_test_name": input_test_name,
                "mapped_test_name": matched_test_name if matched_test_name else "",  # Ensure a non-null string
                "mapped_test_code": matched_test_code if matched_test_code else ""   # Ensure a non-null string
            })

        ref_name = extracted_data.get('referrer_name', "")
        logger.info(f"Mapping ref names to ref code for {ref_name}.")
        matched_ref_name, matched_ref_code, matched_ref_type = map_ref_code(ref_name, threshold)
        extracted_data['mapped_ref_name'] = matched_ref_name or ""
        extracted_data['mapped_ref_code'] = matched_ref_code or ""
        extracted_data['mapped_ref_type'] = matched_ref_type or ""

        # Step 8: Prepare the payload for the external API
        logger.debug(f"Received booking ID: {image_url.booking_id}")
        _id_string = extracted_data.get("_id",{}).get("$oid","")

        combined_result = {
            "_id": _id_string,
            "extracted_data_AI": {
                "doc_date": extracted_data['date'],
                "pt_address": extracted_data['patient_address'],
                "pt_age": extracted_data['patient_age'],
                "pt_age_period": extracted_data['patient_age_period'],
                "pt_contact": extracted_data['patient_contact'],
                "pt_name": extracted_data['patient_name'],
                "pt_sex": extracted_data['patient_sex'],
                "pt_title": extracted_data['patient_title'],
                "ref_name": extracted_data['referrer_name'],
                "ref_type": extracted_data['referrer_type'],
                "mapped_ref_name": extracted_data['mapped_ref_name'],
                "mapped_ref_type": extracted_data['mapped_ref_type'],
                "mapped_ref_code": extracted_data['mapped_ref_code'],
                "remark": extracted_data['remark'],
                "uhid_id": extracted_data['ID'],
                "prescribed_tests": mapped_tests  # Send the mapped tests list, ensuring each field is present
            },
            "created_by": {
                "userId": "system",  # Replace with actual userId if needed
                "CRNID": "system"    # Replace with actual CRNID if needed
            },
            "created_at": datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),
            "booking_id": image_url.booking_id  # Include the booking ID from the user input
        }

        # Step 9: Send the payload to the external API
        logger.info("Sending data to the external API.")
        async with httpx.AsyncClient() as client:
            external_api_response = await client.post("http://localhost:8000/api/v1/prescriptions", json=combined_result)

        if external_api_response.status_code == 201:
            logger.info("Data successfully sent to the external API.")

            # Include the `booking_id` in the final response
            response_data = external_api_response.json()
            response_data["booking_id"] = image_url.booking_id
                    
            return response_data
        else:
            logger.error(f"Failed to send data to the external API. Status code: {external_api_response.status_code}, Response: {external_api_response.text}")
            raise HTTPException(status_code=external_api_response.status_code, detail=f"Failed to send data: {external_api_response.text}")

    except Exception as e:
        logger.error(f"Error during processing: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error during processing: {e}")
