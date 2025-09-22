import time
import json
from typing import Any, Dict, Optional, List, Mapping
import streamlit as st
from google.cloud import firestore
from google.api_core.exceptions import GoogleAPIError
from google.oauth2 import service_account

# Default collection names
DEFAULT_COLLECTIONS = {
    "users": "NeuroTunes_Users",
    "songs": "NeuroTunes_Songs",
    "recommendations": "NeuroTunes_Recommendations",
    "events": "NeuroTunes_Events"
}

def _get_sa_dict() -> Dict[str, Any]:
    """Return service account as dict from st.secrets['gcp_service_account']."""
    try:
        raw = st.secrets.get("gcp_service_account")
        if isinstance(raw, Mapping):
            return dict(raw)
        if isinstance(raw, str):
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
    except Exception as e:
        st.error(f"Error parsing service account: {e}")
    raise RuntimeError("Missing or invalid gcp_service_account in Streamlit secrets")

def _get_fs_config() -> Dict[str, Any]:
    """Load Firestore configuration from secrets."""
    cfg = {}
    sa = _get_sa_dict()
    
    # Project ID from SA or override
    cfg["project_id"] = str(sa.get("project_id") or st.secrets.get("GCP_PROJECT_ID", ""))
    if not cfg["project_id"]:
        raise RuntimeError("Could not determine project_id")
    
    # Collection names with defaults
    col_config = st.secrets.get("collections", {})
    cfg.update({
        f"{k}_col": str(col_config.get(k, v)) 
        for k, v in DEFAULT_COLLECTIONS.items()
    })
    
    cfg["debug"] = bool(st.secrets.get("debug", False))
    return cfg

def _ts_ms() -> int:
    """Return current timestamp in milliseconds."""
    return int(time.time() * 1000)

def _credentials_from_secrets(cfg: Dict[str, Any]) -> Optional[service_account.Credentials]:
    """Return Credentials from service account."""
    try:
        sa = _get_sa_dict()
        # Normalize private key newlines
        if isinstance(sa.get("private_key"), str):
            sa = dict(sa)
            sa["private_key"] = sa["private_key"].replace("\\n", "\n")
        return service_account.Credentials.from_service_account_info(sa)
    except Exception as e:
        if cfg.get("debug"):
            st.error(f"Failed to create credentials: {e}")
        return None

class DDB:
    """Firestore database helper class."""
    
    def __init__(self, project_id: Optional[str] = None):
        self._config = _get_fs_config()
        self._last_error = None
        
        # Initialize Firestore client
        creds = _credentials_from_secrets(self._config)
        project = project_id or self._config["project_id"]
        
        if creds is not None:
            self._client = firestore.Client(
                project=project or getattr(creds, "project_id", None),
                credentials=creds
            )
        else:
            self._client = firestore.Client(project=project) if project else firestore.Client()
        
        # Initialize collections
        self._collections = {
            'users': self._client.collection(self._config["users_col"]),
            'songs': self._client.collection(self._config["songs_col"]),
            'recommendations': self._client.collection(self._config["recommendations_col"]),
            'events': self._client.collection(self._config["events_col"])
        }
    
    def _handle_error(self, error: Exception, operation: str) -> None:
        """Handle and log errors."""
        self._last_error = str(error)
        if self._config.get("debug"):
            st.error(f"Firestore {operation} failed: {error}")
    
    def last_error(self) -> Optional[str]:
        return self._last_error
    
    # User operations
    def upsert_user(self, email: str, name: str) -> bool:
        """Create or update a user."""
        if not email:
            return False
        try:
            self._collections['users'].document(email).set({
                "user_email": email,
                "name": name or "User",
                "updated_at": _ts_ms(),
            }, merge=True, timeout=30.0)
            return True
        except GoogleAPIError as e:
            self._handle_error(e, "upsert_user")
            return False
    
    # Recommendation operations
    def put_recommendations(self, email: str, categories: List[Dict[str, Any]], 
                          cognitive_scores: Optional[Dict[str, Any]] = None) -> bool:
        """Store recommendations for a user."""
        if not email:
            return False
        try:
            data = {
                "user_email": email,
                "updated_at": _ts_ms(),
                "categories": categories or []
            }
            if cognitive_scores:
                data["cognitive_scores"] = cognitive_scores
                
            self._collections['recommendations'].document(email).set(data, timeout=30.0)
            return True
        except GoogleAPIError as e:
            self._handle_error(e, "put_recommendations")
            return False
    
    def get_recommendations(self, email: str) -> Optional[Dict[str, Any]]:
        """Retrieve recommendations for a user."""
        try:
            snap = self._collections['recommendations'].document(email).get(timeout=30.0)
            return snap.to_dict() if snap.exists else None
        except GoogleAPIError as e:
            self._handle_error(e, "get_recommendations")
            return None
    
    # Event logging
    def log_event(self, email: str, event_type: str, payload: Optional[Dict[str, Any]] = None) -> bool:
        """Log an event."""
        try:
            self._collections['events'].add({
                "user_email": email,
                "ts": _ts_ms(),
                "event_type": event_type,
                "payload": payload or {}
            }, timeout=20.0)
            return True
        except GoogleAPIError as e:
            self._handle_error(e, "log_event")
            return False
    
    # Song operations
    def put_song(self, song_id: str, data: Dict[str, Any]) -> bool:
        """Store song data."""
        try:
            self._collections['songs'].document(song_id).set(
                {"song_id": song_id, **data}, 
                timeout=30.0
            )
            return True
        except GoogleAPIError as e:
            self._handle_error(e, "put_song")
            return False
    
    def list_songs(self, category: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """List songs, optionally filtered by category."""
        try:
            query = self._collections['songs']
            if category:
                query = query.where('category', '==', category)
                
            items = []
            for doc in query.stream(timeout=30.0):
                data = doc.to_dict() or {}
                data.update({
                    'song_id': doc.id,
                    'id': doc.id
                })
                items.append(data)
                if limit and len(items) >= limit:
                    break
            return items
        except GoogleAPIError as e:
            self._handle_error(e, "list_songs")
            return []
    
    def health_check(self) -> bool:
        """Verify database connectivity."""
        try:
            next(self._collections['users'].limit(1).stream(timeout=20.0), None)
            return True
        except GoogleAPIError as e:
            self._handle_error(e, "health_check")
            return False
    
    # Catalog management
    _DEFAULT_AUDIO_URLS = {
        "Classical": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
        "Rock": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3",
        "Pop": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3",
        "Rap": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-4.mp3",
        "R&B": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-5.mp3"
    }
    
    def seed_initial_songs(self) -> int:
        """Initialize the song catalog with default tracks."""
        catalog = {
            "Classical": [
                {"id": 1, "name": "Bach's Prelude", "duration": 240, "bpm": 72, "key": "C Major"},
                {"id": 2, "name": "Mozart's Sonata", "duration": 280, "bpm": 68, "key": "G Major"},
                {"id": 3, "name": "Beethoven's Symphony", "duration": 320, "bpm": 76, "key": "F Major"},
                {"id": 4, "name": "Chopin's Nocturne", "duration": 200, "bpm": 65, "key": "D Major"},
                {"id": 5, "name": "Vivaldi's Spring", "duration": 260, "bpm": 80, "key": "A Major"}
            ],
            "Rock": [
                {"id": 10, "name": "Thunder Strike", "duration": 210, "bpm": 140, "key": "E Minor"},
                {"id": 11, "name": "Electric Storm", "duration": 195, "bpm": 145, "key": "A Minor"},
                {"id": 12, "name": "Power Chord", "duration": 180, "bpm": 135, "key": "D Minor"},
                {"id": 13, "name": "Rock Anthem", "duration": 240, "bpm": 130, "key": "G Minor"},
                {"id": 14, "name": "Guitar Hero", "duration": 220, "bpm": 138, "key": "C Minor"}
            ],
            "Pop": [
                {"id": 20, "name": "Catchy Beat", "duration": 180, "bpm": 120, "key": "C Major"},
                {"id": 21, "name": "Dance Floor", "duration": 200, "bpm": 125, "key": "G Major"},
                {"id": 22, "name": "Radio Hit", "duration": 190, "bpm": 118, "key": "F Major"},
                {"id": 23, "name": "Upbeat Melody", "duration": 175, "bpm": 122, "key": "D Major"},
                {"id": 24, "name": "Feel Good", "duration": 185, "bpm": 115, "key": "A Major"}
            ],
            "Rap": [
                {"id": 30, "name": "Street Beats", "duration": 200, "bpm": 95, "key": "E Minor"},
                {"id": 31, "name": "Urban Flow", "duration": 180, "bpm": 88, "key": "A Minor"},
                {"id": 32, "name": "Hip Hop Classic", "duration": 220, "bpm": 92, "key": "D Minor"},
                {"id": 33, "name": "Freestyle", "duration": 160, "bpm": 100, "key": "G Minor"},
                {"id": 34, "name": "Boom Bap", "duration": 195, "bpm": 85, "key": "C Minor"}
            ],
            "R&B": [
                {"id": 40, "name": "Smooth Soul", "duration": 220, "bpm": 75, "key": "C Major"},
                {"id": 41, "name": "Velvet Voice", "duration": 240, "bpm": 70, "key": "G Major"},
                {"id": 42, "name": "Groove Master", "duration": 200, "bpm": 78, "key": "F Major"},
                {"id": 43, "name": "Soulful Nights", "duration": 260, "bpm": 68, "key": "D Major"},
                {"id": 44, "name": "Love Ballad", "duration": 210, "bpm": 72, "key": "A Major"}
            ]
        }

        written = 0
        for category, tracks in catalog.items():
            for track in tracks:
                song_id = str(track["id"]).strip()
                payload = {
                    "name": track.get("name"),
                    "duration": track.get("duration"),
                    "bpm": track.get("bpm"),
                    "key": track.get("key"),
                    "category": category,
                    "url": self._DEFAULT_AUDIO_URLS.get(category, self._DEFAULT_AUDIO_URLS["Classical"]),
                }
                if self.put_song(song_id, payload):
                    written += 1
        return written
