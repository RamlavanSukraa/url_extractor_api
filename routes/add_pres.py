# add_pres.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from fastapi.encoders import jsonable_encoder
from utils.mongo_conn import connect_to_mongo  # Updated import path for db_conn
from utils.logger import app_logger  # Import the logger instance from logger.py
from datetime import datetime

# Use the configured logger from utils
logger = app_logger

# Initialize the router
router = APIRouter()

# Establish a MongoDB connection
client, prescriptions_collection = connect_to_mongo()

# Define data models
class PrescribedTest(BaseModel):
    extracted_test_name: str
    mapped_test_name: str
    mapped_test_code: str

class ExtractedDataAI(BaseModel):
    doc_date: str
    pt_address: str
    pt_age: str
    pt_age_period: str
    pt_contact: str
    pt_name: str
    pt_sex: str
    pt_title: str
    ref_name: str
    ref_type: str
    mapped_ref_name: str
    mapped_ref_type: str
    mapped_ref_code: str
    remark: str
    uhid_id: str
    prescribed_tests: list[PrescribedTest]

class CreatedBy(BaseModel):
    userId: str
    CRNID: str

class PrescriptionCreateData(BaseModel):
    extracted_data_AI: ExtractedDataAI
    created_by: CreatedBy
    created_at: str = Field(
        ...,
        pattern=r'^\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}$',  # Enforce YYYY-MM-DD-HH-MM-SS format
        example="YYYY-MM-DD-HH-MM-SS"
    )
    booking_id: str

# Endpoint to create a prescription entry
@router.post("/api/v1/prescriptions", status_code=201, summary="Create a Prescription Entry", description="Create a new prescription entry with extracted data from the prescription image.")
def create_prescription_entry(prescription: PrescriptionCreateData):

    logger.info(f"Creating a new prescription for user: {prescription.created_by.userId}")
    logger.debug(f"Received booking ID: {prescription.booking_id}")
    try:
        # Validate the date format of `created_at`
        try:
            datetime.strptime(prescription.created_at, "%Y-%m-%d-%H-%M-%S")
            logger.debug(f"'created_at' format is valid: {prescription.created_at}")
        except ValueError:
            logger.error("Invalid 'created_at' format provided.")
            raise HTTPException(status_code=400, detail="Invalid 'created_at' format. Use YYYY-MM-DD-HH-MM-SS.")
        
        # Prepare the data dictionary
        prescription_dict = {
            "extracted_data_AI": prescription.extracted_data_AI.dict(), 
            "created_by": prescription.created_by.dict(),
            "created_at": prescription.created_at,
            "booking_id": prescription.booking_id 
        }

        logger.debug(f"Prepared prescription data for insertion: {jsonable_encoder(prescription_dict)}")

        # Insert into MongoDB and capture the inserted ID
        result = prescriptions_collection.insert_one(prescription_dict)
        object_id = str(result.inserted_id)
        
        logger.info(f"Inserted prescription with ID {object_id}.")

        # Return the response with `_id` as the first field in the desired order
        response_data = {
            "_id": f'ObjectId("{str(prescription_dict["_id"])}")'.replace('"', ''),
            "extracted_data_AI": prescription_dict["extracted_data_AI"],
            "created_by": prescription_dict["created_by"],
            "created_at": prescription_dict["created_at"],
            "booking_id": prescription_dict["extracted_data_AI"].get("booking_id", "N/A")
        }

        logger.debug(f"Response data prepared: {jsonable_encoder(response_data)}")


        return jsonable_encoder(response_data)

    except Exception as e:
        logger.error(f"Error inserting prescription: {e}")
        raise HTTPException(status_code=500, detail="Error inserting prescription.")
