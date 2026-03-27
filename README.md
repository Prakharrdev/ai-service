# JanSamadhan AI Service

This directory contains the AI detection backend for the JanSamadhan V2 platform. It provides real-time pothole detection, CCTV burst analysis, and geocoding services.

## Prerequisites
- **Python 3.10.x** (64-bit)
- Windows / Linux / macOS

## Setup Instructions

1. **Create Virtual Environment**:
   ```powershell
   # If you have Python 3.10 installed as 'py' (Windows default)
   py -3.10 -m venv venv
   
   # Or using absolute path if needed
   # C:\Path\To\Python310\python.exe -m venv venv
   ```

2. **Activate Environment**:
   ```powershell
   # Windows
   .\venv\Scripts\activate
   
   # Linux/macOS
   source venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment**:
   - Copy `.env.example` to `.env`.
   - Update `SUPABASE_URL` and `SUPABASE_SERVICE_KEY`.

5. **Run the Service**:
   ```bash
   # From the ai-service root directory
   uvicorn service.main:app --reload --host 0.0.0.0 --port 8000
   ```

## API Endpoints
- **GET `/health`**: Check service and model status.
- **POST `/cctv/analyze_live`**: Analyze a CCTV camera feed by ID.
- **GET `/geocode`**: Resolve latitude/longitude to DIGIPIN.
- **POST `/infer/image`**: Single image inference.

## Directory Structure
- `service/`: Core logic and API handlers.
- `models/`: Production ONNX models.
- `media/`: Local storage for visual evidence (boxed frames).
