from fastapi import HTTPException
from utils.logger import app_logger
from config import load_config


logger = app_logger
# Load configuration
config = load_config()
MODEL = config['model']


def load_prompt_template(file_path: str) -> str:
    """Load the OpenAI prompt template from a file."""
    try:
        with open(file_path, 'r') as prompt_file:
            return prompt_file.read()
    except FileNotFoundError as e:
        logger.error(f"Prompt template file not found: {e}")
        raise HTTPException(status_code=500, detail="Prompt template file not found.")

def prepare_openai_request(image_url: str, prompt_template: str):
    """Prepare OpenAI request payload."""
    return {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant that responds in JSON format. Help me to get the patient's data and prescribed pathological lab tests extracted from the prescription given by a doctor, hospital, or lab."
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt_template},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]
            }
        ],
        "temperature": 0.0,
    }