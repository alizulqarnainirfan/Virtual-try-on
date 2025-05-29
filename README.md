# 🧥 Virtual Try-On (VTON) API

A production-ready API for virtual clothing try-on built using **FastAPI** and powered by the **Pixelcut AI API**. This application allows users to upload a photo of a person and a garment, and returns a realistic try-on result image. It's designed with robust image validation, error handling, rate limiting, and Docker-based deployment.

---

## 🚀 Features

- ✨ AI-powered virtual try-on using Pixelcut
- 📤 Upload person and garment images (JPEG/PNG)
- ✅ Image validation via Pillow
- 🔁 Async external API communication using HTTPX
- 🛡️ Abuse prevention with request rate limiting (2 requests per 5 minutes per IP)
- 🔄 Cross-Origin support via CORS
- 🐳 Fully Dockerized for easy deployment
- ☁️ Hosted on Hugging Face Spaces

---

## 🧪 Demo

**Live Demo:** [Try it on Hugging Face](https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE_NAME)

---

## 📷 How It Works

1. Upload a **person image** and a **garment image** to the `/vton/` endpoint.
2. The FastAPI backend validates and forwards the images to the **Pixelcut API**.
3. Pixelcut processes and returns a try-on image URL.
4. The result image is downloaded and returned as a downloadable response.

---

## 🔧 Tech Stack

- **Backend:** FastAPI
- **AI API:** Pixelcut
- **Image Handling:** Pillow
- **HTTP Client:** HTTPX (async)
- **Rate Limiting:** SlowAPI
- **Environment Management:** python-dotenv
- **Deployment:** Docker, Hugging Face Spaces

---

---

## 🛠️ Setup & Installation

### 1. Clone the Repo

1. bash
git clone https://github.com/YOUR_USERNAME/virtual-tryon-api.git
cd virtual-tryon-api

2. Create .env file
Create a .env file in the root directory and add:
PIXEL_CUT_API_KEY=your_pixelcut_api_key
PIXEL_CUT_API_ENDPOINT=https://api.pixelcut.ai/v1/virtual-tryon

4. Install Dependencies
pip install -r requirements.txt

5. Run Locally
uvicorn app.main:app --reload

6. Docker Build & Run
docker build -t vton-api .
docker run -p 7860:7860 vton-api

📦 API Usage
POST /vton/
Description: Generate a virtual try-on result using a person image and a garment image.

Form Data:

person_image (JPEG/PNG)

garment_image (JPEG/PNG)

Response: Returns the merged try-on image as a downloadable file.

⚠️ Rate Limiting
Each IP is limited to 2 requests every 5 minutes to avoid abuse of the external API.

✅ TODO (Optional Enhancements)
Add front-end interface for easier testing

Implement user authentication and API key-based access

Add image resolution validation

Store results in cloud storage for caching

🙌 Acknowledgements
Pixelcut API

FastAPI

Hugging Face Spaces

📄 License
MIT License. Feel free to fork and modify!

👤 Author
Ali Zulqarnain
AI/ML Engineer 
https://www.linkedin.com/in/alizulqarnainirfan/
