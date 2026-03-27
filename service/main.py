from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

try:
    from service.onnx_inference_service import InferenceConfig, OnnxInferenceService
except ModuleNotFoundError:
    # Supports direct run: python service/main.py
    from onnx_inference_service import InferenceConfig, OnnxInferenceService

# Updated model path for consolidated ai-service structure
DEFAULT_MODEL = str(Path(__file__).parent.parent / "models/best.onnx")
MODEL_PATH = os.getenv("MODEL_PATH", DEFAULT_MODEL)

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="JanSamadhan AI Service", version="1.0.0")

# Enable CORS for browser-based frontend calls
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HealthResponse(BaseModel):
    ok: bool
    model_path: str
    model_version: str
    status: str

class ErrorDetail(BaseModel):
    code: str
    message: str
    timestamp: str

class ErrorResponse(BaseModel):
    error: ErrorDetail

class CameraAnalyzeRequest(BaseModel):
    camera_id: str

def _error_response(code: str, message: str, status_code: int = 400):
    from fastapi.responses import JSONResponse
    from datetime import datetime
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )


def _create_service() -> OnnxInferenceService:
    model_path = Path(MODEL_PATH).resolve()
    if not model_path.exists():
        msg = f"CRITICAL: Detector model missing at {model_path}. Please check AI Service installation."
        print(msg)
        return None # Allow app to start so /health can report error

    print(f"INFO: Initializing detector signal from {model_path}")
    return OnnxInferenceService(
        model_path=model_path,
        config=InferenceConfig(conf=0.35, iou=0.7, imgsz=640, device="0"),
    )


# Lazy init
_service: OnnxInferenceService | None = None


def get_service() -> OnnxInferenceService:
    global _service
    if _service is None:
        _service = _create_service()
    if _service is None:
        raise FileNotFoundError("AI Model not found on server.")
    return _service


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Standard health check for service monitoring."""
    try:
        service = get_service()
        return HealthResponse(
            ok=True, 
            model_path=service.model_path, 
            model_version="v2.0-stable",
            status="READY"
        )
    except Exception as e:
        return HealthResponse(
            ok=False,
            model_path=MODEL_PATH,
            model_version="unknown",
            status=f"ERROR: {str(e)}"
        )


@app.post("/infer/image")
async def infer_image(file: UploadFile = File(...)) -> dict:
    if not file.content_type or not file.content_type.startswith("image/"):
        return _error_response("BAD_REQUEST", "Only image uploads are supported")

    image_bytes = await file.read()
    if not image_bytes:
        return _error_response("BAD_REQUEST", "Empty file")

    service = get_service()
    import time
    start = time.time()
    result = service.predict_image_bytes(image_bytes)
    latency = (time.time() - start) * 1000

    return {
        "source_filename": file.filename,
        "model_version": "v2.0-stable",
        "latency_ms": round(latency, 2),
        **result,
    }


# ============================================================================
# SURVEILLANCE & COMMAND CENTER ENDPOINTS
# ============================================================================


@app.get("/geocode")
async def geocode(lat: float, lng: float):
    """Simple mock geocoder for Digipin resolution."""
    # Logic: First 5 digits of coords + '+'
    digipin = f"{str(lat)[:5]}+{str(lng)[:5]}".replace(".", "")
    return {"digipin": digipin[:9]}


@app.post("/cctv/analyze_live")
async def cctv_analyze_live(request: CameraAnalyzeRequest) -> dict:
    """
    Download video from camera's URL, extract burst frames, and run analysis.
    """
    try:
        from service.supabase_client import get_camera
        from service.cctv_handler import get_cctv_auto_handler
    except ModuleNotFoundError:
        from supabase_client import get_camera
        from cctv_handler import get_cctv_auto_handler

    camera = get_camera(request.camera_id)
    if not camera:
        return _error_response("NOT_FOUND", "Camera not found", status_code=404)

    video_url = camera.get("video_url")
    if not video_url:
        return _error_response("BAD_REQUEST", "Camera has no video URL")

    # Download video to temp file
    import requests
    import tempfile
    import cv2
    from PIL import Image

    print(f"INFO: Downloading video from {video_url}")
    try:
        r = requests.get(video_url, timeout=30)
        r.raise_for_status()
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp.write(r.content)
            tmp_path = tmp.name
    except Exception as e:
        return _error_response("DOWNLOAD_FAILED", f"Failed to download video: {str(e)}")

    # Extract 10 frames spread across the video
    burst_data = []
    best_frame = None
    max_conf = 0
    
    cap = cv2.VideoCapture(tmp_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Take 10 samples
    indices = [int(i * (total_frames - 1) / 9) for i in range(10)] if total_frames > 10 else range(total_frames)
    
    service = get_service()
    
    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if not ret: continue
        
        # Convert to PIL for inference
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(frame_rgb)
        
        # Run inference
        result = service._predict_common(pil_img)
        burst_data.append(result["detections"])
        
        # Keep track of best frame for visual evidence
        if result["best_confidence"] > max_conf:
            max_conf = result["best_confidence"]
            best_frame = pil_img

    cap.release()
    import os
    try: os.unlink(tmp_path)
    except: pass

    if not burst_data:
        return _error_response("INFERENCE_FAILED", "Could not extract any frames from video")

    handler = get_cctv_auto_handler()
    # Process the burst with reliability engine
    result = handler.process_burst(request.camera_id, burst_data, best_frame=best_frame)
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
