import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client
from typing import Optional, Dict, List, Any

# Load environment variables from the ai-service root
ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env", override=True)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    # Fallback for CI/Initial setup: allow it to be missing but warn
    print("WARNING: SUPABASE_URL or SUPABASE_SERVICE_KEY missing from .env")
else:
    print(f"DEBUG: Loaded URL: {SUPABASE_URL}")
    print(f"DEBUG: Key starts with: {SUPABASE_SERVICE_KEY[:10]}... ends with: {SUPABASE_SERVICE_KEY[-10:]}")

_client: Optional[Client] = None

def get_supabase() -> Client:
    global _client
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
            raise ValueError("Supabase environment variables NOT properly set.")
        _client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    return _client

def get_camera(camera_id: str) -> Optional[Dict[str, Any]]:
    """Fetch camera details by ID."""
    try:
        sb = get_supabase()
        res = sb.table("cctv_cameras").select("*").eq("id", camera_id).single().execute()
        return res.data if res.data else None
    except Exception as e:
        print(f"ERROR fetching camera {camera_id}: {e}")
        return None

def list_cameras() -> List[Dict[str, Any]]:
    """List all active cameras."""
    try:
        sb = get_supabase()
        res = sb.table("cctv_cameras").select("*").execute()
        return res.data if res.data else []
    except Exception as e:
        print(f"ERROR listing cameras: {e}")
        return []

def find_duplicate_complaint(latitude: float, longitude: float, hours_back: int = 24) -> Optional[Dict[str, Any]]:
    """Check for recent duplicate tickets at the same location."""
    try:
        sb = get_supabase()
        from datetime import datetime, timedelta, timezone
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours_back)).isoformat()
        
        # Precise Lat/Lon match for demo
        res = sb.table("complaints").select("*").eq("latitude", latitude).eq("longitude", longitude).gt("created_at", cutoff).in_("status", ["new", "assigned", "pending_verification"]).order("created_at", desc=True).limit(1).execute()
        
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"ERROR checking duplicates: {e}")
        return None

def create_complaint(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new complaint ticket in Supabase."""
    sb = get_supabase()
    res = sb.table("complaints").insert(data).execute()
    if not res.data:
        raise Exception("Failed to insert complaint into Supabase")
    return res.data[0]

def update_camera_status(camera_id: str, status: str):
    """Update camera's last known status."""
    try:
        sb = get_supabase()
        sb.table("cctv_cameras").update({"last_status": status}).eq("id", camera_id).execute()
    except Exception as e:
        print(f"ERROR updating camera status: {e}")

def log_analysis(log_data: Dict[str, Any]):
    """Log the AI analysis result."""
    try:
        sb = get_supabase()
        sb.table("cctv_analysis_logs").insert(log_data).execute()
    except Exception as e:
        print(f"ERROR logging analysis: {e}")

def log_detection(camera_id: str, digipin: str, confidence: float, timestamp: str = None):
    """Stub for telemetry logging."""
    pass

def update_suspected_incident(digipin: str, status: str, confidence: float, camera_id: str, timestamp: str = None):
    """Stub for suspected incident tracking."""
    pass

def get_system_user_id() -> str:
    """Return the ID for the system user responsible for CCTV tickets."""
    # Production Admin ID
    return '0e3a680d-b896-4b74-940c-c68a2201503c'
