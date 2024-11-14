<<<<<<< HEAD
# temp_repo
this is temp repo
=======
# Prescription Data Extraction API - Sukraa AI

**Disclaimer**: This is a private repository owned by Sukraa Software Solution Pvt. Ltd. All information contained herein is confidential and proprietary. Unauthorized access, use, or distribution is strictly prohibited.

This project provides a FastAPI-based application for extracting patient data and prescribed tests from prescription images. It allows users to upload images in various formats, which are then processed to extract relevant information using OpenAI's API.

## Table of Contents

- [Features](#features)
- [Technologies Used](#technologies-used)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Endpoints](#api-endpoints)
- [How It Works](#how-it-works)

## Features

- **Image Upload**: Supports uploading prescription images in formats such as PNG, JPG, JPEG, GIF, and WEBP.
- **Data Extraction**: Extracts patient data and prescribed tests from the uploaded prescription images.
- **Base64 Encoding**: Encodes uploaded images into base64 strings for API consumption.
- **Image Compression**: Compresses images to reduce file size while maintaining quality.

## Technologies Used

- **FastAPI**: A modern web framework for building APIs with Python 3.6+ based on standard Python type hints.
- **OpenAI**: Utilizes OpenAI's API for data extraction from prescription images.
- **Pillow**: A Python Imaging Library to handle image processing.
- **Python**: The primary programming language for the project.
- **Uvicorn**: An ASGI server for running the FastAPI application.

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/ayush-sukraa/sukraa-ai-aux.git
   cd sukraa-ai-aux/apis/dataExtractor
   ```

2. **Create a virtual environment** (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install the required packages**:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

Before running the application, set up your `config.ini` file in the project root with the following format:

```ini
[OPENAI]
api_key = YOUR_OPENAI_API_KEY
model = YOUR_OPENAI_MODEL

[IMAGE]
max_size = 0.5  # Maximum image size in MB
```

## Usage

1. **Run the application**:
   ```bash
   uvicorn app:app --reload
   ```

2. **Access the API**: Open your browser and navigate to `http://127.0.0.1:8000/docs` to view the automatically generated Swagger UI, where you can test the API endpoints.

## API Endpoints

- **POST /encode_image/**
  - Upload an image file to encode it into a base64 string.
  - **Request**: Multipart form-data with the file field.
  - **Response**: JSON object containing the encoded image string.

- **POST /extract_prescription/**
  - Upload an image file of a prescription to extract patient data and prescribed tests.
  - **Request**: Multipart form-data with the file field.
  - **Response**: JSON object containing extracted patient details and prescribed tests.

## How It Works

1. **Image Validation**: Uploaded images are validated to ensure they are in the supported formats.
2. **Image Compression**: Images are compressed to a specified size limit while maintaining their quality.
3. **Data Extraction**: The compressed images are sent to OpenAI's API, which processes the images and extracts the relevant data.
4. **Response**: The extracted data is returned as a JSON response.
>>>>>>> fffbe56 (Initial commit)
