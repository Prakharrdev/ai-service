"""
CCTV feature handler for JanSamadhan V2.
Features:
1. /cctv/process - Auto-ticket generation from CCTV frame detections
2. /cctv/verify - Proof verification (before/after comparison)
"""

from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import json
from PIL import Image
import io
import logging
import os
from dotenv import load_dotenv

logger = logging.getLogger("CCTVHandler")

# Load environment variables
load_dotenv()

try:
    from service.supabase_client import (
        get_camera,
        list_cameras,
        create_complaint,
        find_duplicate_complaint,
        log_analysis,
        update_camera_status,
        log_detection,
        update_suspected_incident,
        get_system_user_id
    )
except ModuleNotFoundError:
    from supabase_client import (
        get_camera,
        list_cameras,
        create_complaint,
        find_duplicate_complaint,
        log_analysis,
        update_camera_status,
        log_detection,
        update_suspected_incident,
        get_system_user_id
    )

def _compute_digipin(lat: float, lon: float) -> str:
    """Mock DIGIPIN generator for demo."""
    return f"{str(lat)[:5]}+{str(lon)[:5]}"


class CCTVAutoTicketHandler:
    """Handle CCTV to auto-ticket generation."""

    @property
    def CONF_THRESHOLD_HIGH(self) -> float:
        return float(os.getenv("CONF_THRESHOLD", 0.35))

    @property
    def CONF_THRESHOLD_LOW(self) -> float:
        return float(os.getenv("WEAK_THRESHOLD", 0.25))

    @property
    def BURST_WINDOW_SECONDS(self) -> int:
        return int(os.getenv("TIME_WINDOW_SEC", 30))

    @property
    def DUP_HOURS(self) -> int:
        return int(os.getenv("DUP_HOURS", 24))

    CITIZEN_CORROB_HOURS = 24
    HOTSPOT_WINDOW_HOURS = 144
    PERSISTENCE_DAYS_ESCALATION = 21

    def __init__(self):
        # System account for CCTV tickets
        self.system_citizen = {"id": get_system_user_id()}

    def process_burst(self, camera_id: str, burst_data: List[List[Dict[str, Any]]], timestamps: List[str] = None, best_frame: Image.Image = None) -> Dict[str, Any]:
        """
        Process a high-recall burst of (typically 10) frames.
        """
        camera = get_camera(camera_id)
        if not camera:
            return {"error": f"Camera {camera_id} not found"}

        digipin = _compute_digipin(camera["latitude"], camera["longitude"])
        now = datetime.utcnow().isoformat()
        
        # Duplicate block check
        duplicate = find_duplicate_complaint(camera["latitude"], camera["longitude"], hours_back=24)
        if duplicate:
            return {"status": "duplicate_prevented", "complaint_id": duplicate["id"]}

        # Log telemetry
        valid_detections = []
        for i, frame_detections in enumerate(burst_data):
            ts = timestamps[i] if (timestamps and i < len(timestamps)) else now
            for det in frame_detections:
                if det.get("class") == "pothole" or det.get("class_name") == "pothole":
                    valid_detections.append(det)

        if not valid_detections:
            return {"status": "no_signals_detected", "digipin": digipin}

        # Reliability Engine
        trigger_meta = self._check_reliability_triggers(digipin)
        triggered = trigger_meta.get("triggered", False)

        if triggered:
            # Create auto-ticket
            best_det = max(valid_detections, key=lambda d: d.get("confidence", 0))
            severity, escalation_msg = self._calculate_severity(digipin, trigger_meta["rule"], best_det["confidence"])
            category_id = 15 if camera.get("road_type") == "colony" else 11

            # Visual Evidence
            photo_url = None
            if best_frame:
                try:
                    # In relocated service, use main as service entry
                    from service.main import get_service
                    service = get_service()
                    boxed_img = service.draw_detections(best_frame, [best_det])
                    
                    # Store in ai-service/media
                    media_dir = Path(__file__).resolve().parents[1] / "media" / "cctv_proofs"
                    media_dir.mkdir(parents=True, exist_ok=True)
                    filename = f"ticket_{digipin}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                    file_path = media_dir / filename
                    boxed_img.save(file_path, "JPEG", quality=85)
                    photo_url = str(file_path.absolute())
                except Exception as e:
                    logger.error(f"[VISUAL EVIDENCE] Processing failed: {e}")

            complaint = create_complaint({
                "citizen_id": self.system_citizen["id"],
                "category_id": category_id,
                "title": f"CCTV Detected: Pothole at {camera['name']}",
                "description": f"Automatically detected by CCTV network at {camera['name']}.",
                "internal_notes": f"Triggered by {trigger_meta['rule']}. {escalation_msg} Max Confidence: {best_det['confidence']:.1%}.",
                "latitude": camera["latitude"],
                "longitude": camera["longitude"],
                "severity": severity,
                "assigned_department": camera.get("assigned_department", "MCD"),
                "source": "cctv",
                "camera_id": camera_id,
                "photo_url": photo_url,
                "external_data": {
                    "digipin": digipin,
                    "trigger_rule": trigger_meta["rule"],
                    "burst_size": len(burst_data)
                }
            })
            
            log_analysis({
                "camera_id": camera_id,
                "complaint_id": complaint["id"],
                "status_result": "Ticket Generated",
                "ai_metadata": trigger_meta
            })
            update_camera_status(camera_id, "Ticket Generated")
            
            return {
                "status": "ticket_created",
                "complaint_id": complaint["id"],
                "trigger_rule": trigger_meta.get("rule", "T1_MULTI_FRAME_CONFIRMATION"),
                "severity": severity
            }
        else:
            return {
                "status": "signal_buffered_suspected",
                "digipin": digipin,
                "message": "Signal confirmed but threshold for auto-ticket not yet met."
            }

    def _check_reliability_triggers(self, digipin: str) -> Dict[str, Any]:
        """Mock reliability check for demo."""
        # In a real system, this queries telemetry. 
        # For the demo migration, we trigger T1 if ANY valid detections exist in a burst.
        return {"triggered": True, "rule": "T1_MULTI_FRAME_CONFIRMATION"}

    def _calculate_severity(self, digipin: str, trigger_rule: str, best_conf: float) -> tuple[str, str]:
        if best_conf >= 0.8: return "L3_HIGH", "Ultra-high confidence detection."
        if best_conf >= 0.5: return "L2_MEDIUM", "Standard detection."
        return "L1_LOW", "Weak signal confirmation."


def get_cctv_auto_handler():
    return CCTVAutoTicketHandler()
