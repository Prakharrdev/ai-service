"""
WhatsApp entry point handler for JanSamadhan V2.
Receives Twilio webhook -> extracts image + text -> calls analyze -> creates complaint.
"""

import base64
import json
from typing import Dict, Any, Optional
from io import BytesIO
from pathlib import Path

try:
    from service.supabase_client import create_complaint
except ModuleNotFoundError:
    from supabase_client import create_complaint


class WhatsAppMessage:
    """Parse Twilio WhatsApp webhook payload."""

    def __init__(self, webhook_payload: Dict[str, Any]):
        self.payload = webhook_payload
        self.phone = webhook_payload.get("From", "").replace("whatsapp:", "")
        self.message_type = webhook_payload.get("MediaType", "text")  # text, image, location, etc.

    def extract_image_bytes(self) -> Optional[bytes]:
        """Extract image bytes if message contains media."""
        # For now, return None (would be fetched in real Twilio integration)
        return None

    def extract_text(self) -> str:
        """Extract caption/text from message."""
        return self.payload.get("Body", "")

    def extract_location(self) -> tuple[float, float]:
        """Extract location if shared (Twilio sends Latitude/Longitude)."""
        lat = self.payload.get("Latitude")
        lon = self.payload.get("Longitude")
        if lat and lon:
            return (float(lat), float(lon))
        return None


class WhatsAppHandler:
    """Handle WhatsApp flow: image + caption -> analyze -> create complaint."""

    def __init__(self):
        pass

    def process_incoming_message(self, twilio_webhook: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process incoming Twilio WhatsApp message.
        """
        msg = WhatsAppMessage(twilio_webhook)
        phone = msg.phone

        if not phone:
            return {"error": "No phone found in webhook"}

        # Basic stub for ported flow
        return {
            "status": "received",
            "phone": phone,
            "message": "JanSamadhan AI received your report. Please use the mobile app for better location tracking."
        }


# Singleton handler
_handler = None

def get_whatsapp_handler():
    global _handler
    if _handler is None:
        _handler = WhatsAppHandler()
    return _handler
