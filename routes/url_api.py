from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import json
from datetime import datetime
import httpx

from config import load_config
from openai import OpenAI

# Utils
from utils.logger import app_logger
from utils.testMap_utils import map_ref_code, map_test_code
from utils.utils import to_empty_string
from utils.openai_utils import prepare_openai_request, load_prompt_template

# Setup logging
logger = app_logger

# Load configuration
config = load_config()
API_KEY = config['api_key']
THRESHOLD = config['threshold']
client = OpenAI(api_key=API_KEY)

# Define the Router
router = APIRouter()

# Define request model
class ExtractionRequest(BaseModel):
    url: str
    booking_id: str


@router.post("/extract_and_map_tests_url/")
async def extract_and_map_tests(request: ExtractionRequest):
    """
    Extracts patient details from the given image URL and maps them to test codes.
    """
    logger.info("Starting patient details extraction and mapping process.")

    try:
        # Step 1: Load Prompt Template for OpenAI Request
        logger.info("Loading prompt template for OpenAI request.")
        prompt_template = load_prompt_template('prompt_template.txt')

        # Step 2: Prepare OpenAI Request Payload for Openai API
        logger.info("Preparing request payload for OpenAI API.")
        request_payload = prepare_openai_request(request.url, prompt_template)

        # Step 3: Call OpenAI API with Timeout
        logger.info("Sending request to OpenAI API.")
        try:
            response = client.chat.completions.create(**request_payload, timeout=120) 
            logger.info("Received response from OpenAI API.")
        except Exception as e:
            logger.error(f"OpenAI API communication error: {e}")
            raise HTTPException(status_code=500, detail=f"OpenAI API error: {str(e)}")

        # Step 4: Parse OpenAI Response
        try:
            gpt_response = json.loads(
                response.choices[0].message.content.split('```json')[-1].split('```')[0]
            )
            logger.info("Response parsed successfully.")
        except (json.JSONDecodeError, IndexError) as e:
            logger.error(f"Failed to parse OpenAI API response: {e}")
            raise HTTPException(status_code=500, detail="Failed to parse OpenAI response.")

        # Step 5: Map Test Names
        logger.info("Mapping test names from GPT response.")
        test_names = gpt_response.get("prescribed_test", [])
        if not test_names:
            logger.warning("No test names found in the response.")
            raise HTTPException(status_code=400, detail="No test names found in the extracted data.")

        mapped_tests = [
            {
                "input_test_name": name,
                "matched_test_name": mapped_name,
                "matched_test_code": mapped_code
            }
            for name in test_names
            if (mapped_name := map_test_code(name, THRESHOLD)[0]) and
               (mapped_code := map_test_code(name, THRESHOLD)[1])
        ]
        logger.info(f"Successfully mapped {len(mapped_tests)} test names.")

        # Step 6: Map Referrer Information
        ref_name = gpt_response.get("referrer_name", "")
        matched_ref_name, matched_ref_code, matched_ref_type = map_ref_code(ref_name, THRESHOLD)
        logger.info("Referrer information mapped successfully.")

        # Step 7: Prepare Payload
        logger.info("Preparing payload for external API.")
        payload = {
            "extracted_data_AI": {
                "doc_date": to_empty_string(gpt_response.get("date")),
                "pt_address": to_empty_string(gpt_response.get("patient_address")),
                "pt_contact": to_empty_string(gpt_response.get("patient_contact")),
                "pt_name": to_empty_string(gpt_response.get("patient_name")),
                "pt_sex": to_empty_string(gpt_response.get("patient_sex")),
                "pt_title": to_empty_string(gpt_response.get("patient_title")),
                "ref_name": to_empty_string(gpt_response.get("referrer_name")),
                "ref_type": to_empty_string(gpt_response.get("referrer_type")),
                "pt_age": to_empty_string(str(gpt_response.get("patient_age", "Unknown"))),
                "pt_age_period": to_empty_string(gpt_response.get("patient_age_period", "Unknown")),
                "mapped_ref_name": to_empty_string(matched_ref_name),
                "mapped_ref_type": to_empty_string(matched_ref_type),
                "mapped_ref_code": to_empty_string(matched_ref_code),
                "remark": to_empty_string(gpt_response.get("remark")),
                "uhid_id": to_empty_string(gpt_response.get("ID")),
                "prescribed_tests": [
                    {
                        "extracted_test_name": to_empty_string(test.get("input_test_name")),
                        "mapped_test_name": to_empty_string(test.get("matched_test_name")),
                        "mapped_test_code": to_empty_string(test.get("matched_test_code"))
                    }
                    for test in mapped_tests
                ],
            },
            "created_by": {
                "userId": "system",
                "CRNID": "system"
            },
            "created_at": datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),
            "booking_id": request.booking_id,
        }

        # Step 8: Send Data to External API with Timeout
        logger.info("Sending data to the external API...")
        async with httpx.AsyncClient() as http_client:
            try:
                external_api_response = await http_client.post(
                    "http://51.20.150.57:5009/api/v1/prescriptions",
                    json=payload,
                    timeout=120
                )
            except httpx.RequestError as e:
                logger.error(f"External API communication error: {e}")
                raise HTTPException(status_code=500, detail="External API request failed.")

        # Step 9: Handle External API Response
        if external_api_response.status_code == 201:
            logger.info("Data successfully saved in MongoDB.")
            response_data = external_api_response.json()
            response_data["booking_id"] = request.booking_id

            if '_id' in response_data:
                response_data['_id'] = str(response_data['_id']).replace("ObjectId(", "").replace(")", "").strip()
                logger.info(f"Formatted MongoDB _id: {response_data['_id']}")

            return response_data
        else:
            logger.error(f"Failed to send data to the external API. "
                         f"Status code: {external_api_response.status_code}, Response: {external_api_response.text}")
            raise HTTPException(status_code=external_api_response.status_code, detail=f"Failed to send data: {external_api_response.text}")

    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")
