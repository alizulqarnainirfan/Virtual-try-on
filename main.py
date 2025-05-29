# Necessities
import os
import uuid
import json
import logging
import httpx

from io import BytesIO
from PIL import Image, UnidentifiedImageError
from dotenv import load_dotenv

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from fastapi.exceptions import RequestValidationError
from fastapi import FastAPI, UploadFile, File, HTTPException, status, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi


# --- Configuration ---
# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(override=True)

PIXEL_CUT_API_KEY = os.getenv("PIXEL_CUT_API_KEY")
PIXEL_CUT_API_ENDPOINT = os.getenv("PIXEL_CUT_API_ENDPOINT")

# Validate environment variables early
if not PIXEL_CUT_API_KEY:

    logger.critical("PIXEL_CUT_API_KEY is not set in the .env file. Please set it for production.")
    raise ValueError("PIXEL_CUT_API_KEY must be set in the .env file")

if not PIXEL_CUT_API_ENDPOINT:

    logger.critical("PIXEL_CUT_API_ENDPOINT is not set in the .env file. Please set it for production.")
    raise ValueError("PIXEL_CUT_API_ENDPOINT must be set in the .env file")

# --- FastAPI App Setup ---

app = FastAPI(

    title="Virtual Try On",
    version="1.0.0",
    description="API endpoint for a clothing virtual try-on using an external AI service. "
                "Accepts JPEG and PNG images."

)

# Configurations for slowapi to prevent abuse & add rate limit
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
# app.add_exception_handler(RequestValidationError, _rate_limit_exceeded_handler)


# Add custom rate limit exception handler
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": "Rate limit exceeded. You can only make 2 requests every 5 minutes. Please try again later."}
    )

app.add_exception_handler(RequestValidationError, _rate_limit_exceeded_handler)


app.add_middleware(

    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]

)


# --- Routes ---
@app.get("/")

def root():
    return {"message": "Virtual Try On is Running ⚡"}


@app.post("/vton/")
@limiter.limit("2/5minutes")  # Limited to 2 requests per 5 minutes per user, through IP address

async def virtual_try_on(

    request : Request,
    person_image: UploadFile = File(..., description="Image of the person to try on clothes. Formats: JPEG, PNG."),
    garment_image: UploadFile = File(..., description="Image of the garment to be tried on. Formats: JPEG, PNG.")

):

    allowed_image_types = ["image/jpeg", "image/png"]

    # Validate file types

    for img_file, img_name in [(person_image, "person_image"), (garment_image, "garment_image")]:
 
        if img_file.content_type not in allowed_image_types:
 
            logger.warning(f"Invalid {img_name} content type: {img_file.content_type}")
            raise HTTPException(
 
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{img_name.replace('_', ' ').capitalize()} must be JPEG or PNG."
 
            )

        img_file.file.seek(0)

    try:
        # Load images with PIL just to ensure they are valid image files,
        # but NOT for resolution validation.
        # This will still raise UnidentifiedImageError if the file isn't a proper image.
        person_pil_image = Image.open(person_image.file)
        garment_pil_image = Image.open(garment_image.file)
        
        # Re-seek file pointers after PIL.Image.open to ensure httpx reads from start
        person_image.file.seek(0)
        garment_image.file.seek(0)

        files_for_api = {
 
            "person_image": (person_image.filename, person_image.file, person_image.content_type),
            "garment_image": (garment_image.filename, garment_image.file, garment_image.content_type)
 
        }

        headers = {
 
            "X-API-KEY": PIXEL_CUT_API_KEY,
            "Accept": "application/json"
 
        }

        logger.info(f"Calling Pixelcut API at {PIXEL_CUT_API_ENDPOINT}")
 
        async with httpx.AsyncClient(timeout=60.0) as client: # Increased timeout for external API
 
            response = await client.post(PIXEL_CUT_API_ENDPOINT, headers=headers, files=files_for_api)
        
        response.raise_for_status() # Raises an exception for 4xx/5xx responses

        try:
            result_json = response.json()
 
        except json.JSONDecodeError:
            logger.error(f"Pixelcut API returned invalid JSON: {response.text}")
 
            raise HTTPException(
 
                status_code=status.HTTP_502_BAD_GATEWAY, # Bad Gateway for malformed upstream response
                detail="External service returned unparseable response."
 
            )

        image_url = result_json.get("image_url") or result_json.get("url") or result_json.get("result_url")

        if not image_url:
 
            logger.error(f"Pixelcut API response missing image URL. Response: {result_json}")
            raise HTTPException(
 
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="External VTON service did not return an image URL."
 
            )

        logger.info(f"Downloading result image from: {image_url}")
 
        async with httpx.AsyncClient(timeout=60.0) as client: # Increased timeout for image download
            image_response = await client.get(image_url)
 
        image_response.raise_for_status() # Raises an exception for 4xx/5xx responses

        try:
            # Using BytesIO to open from content, as image_response.content is bytes
            image_bytes_io = BytesIO(image_response.content)
            image_bytes_io.seek(0) # Ensure pointer is at beginning
            image = Image.open(image_bytes_io)
 
        except UnidentifiedImageError:
            logger.error("Downloaded file from Pixelcut is not a valid image.")
            raise HTTPException(
 
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="External service returned an invalid or corrupted image."
 
            )

        # Prepare image for streaming response
        img_io = BytesIO()
 
        # Ensure format is supported by PIL save; default to PNG if not or unknown
        img_format = image.format if image.format and image.format.upper() in ["PNG", "JPEG", "JPG"] else "PNG"
        image.save(img_io, format=img_format)
        img_io.seek(0)

        media_type = f"image/{img_format.lower()}"
        filename = f"tryon_{uuid.uuid4().hex}.{img_format.lower()}"

        logger.info(f"Successfully generated and streaming try-on image: {filename}")
        return StreamingResponse(
 
            img_io,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
 
        )

    except HTTPException: # Re-raise HTTPExceptions as they are meant for client responses
        raise
 
    except httpx.RequestError as e: # Catch httpx specific network/request errors
        logger.error(f"Network or API communication error with Pixelcut: {e}")
 
        raise HTTPException(
 
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, # Service Unavailable for network issues
            detail=f"Failed to communicate with external VTON service. Please try again later. ({e})"
 
        )
    except Exception as e:
        logger.exception("An unexpected error occurred during VTON process.") # Logs traceback automatically
 
        raise HTTPException(
 
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected internal error occurred: {e}"
 
        )



@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(openapi_url="/openapi.json", title="API Docs")

@app.get("/openapi.json", include_in_schema=False)
async def openapi():
    return get_openapi(title=app.title, version=app.version, routes=app.routes)
