import time
from typing import Any, Dict, Optional, List

import streamlit as st
from google.cloud import firestore
from google.api_core.exceptions import GoogleAPIError

"""Strict Firestore configuration from Streamlit secrets.

Required structure in .streamlit/secrets.toml:

[firestore]
project_id = "your-project-id"
debug = true  # optional

[firestore.collections]
users = "NeuroTunes_Users"
songs = "NeuroTunes_Songs"
recommendations = "NeuroTunes_Recommendations"
events = "NeuroTunes_Events"

# optional for local/dev
[firestore.service_account]
# ... service account json fields ...
"""
def _get_fs_config() -> Dict[str, Any]:
    cfg: Dict[str, Any] = {}
    try:
        fs = st.secrets.get("firestore")
    except Exception:
        fs = None
    if not isinstance(fs, dict):
        raise RuntimeError("Missing [firestore] configuration in Streamlit secrets.")

    project_id = fs.get("project_id")
    if not project_id or not isinstance(project_id, str):
        raise RuntimeError("firestore.project_id must be set in Streamlit secrets.")
    cfg["project_id"] = project_id

    collections = fs.get("collections")
    if not isinstance(collections, dict):
        raise RuntimeError("firestore.collections must be a table with required keys: users, songs, recommendations, events.")
    required_keys = ["users", "songs", "recommendations", "events"]
    missing = [k for k in required_keys if not collections.get(k)]
    if missing:
        raise RuntimeError(f"Missing firestore.collections keys: {', '.join(missing)}")
    cfg["users_col"] = str(collections["users"]).strip()
    cfg["songs_col"] = str(collections["songs"]).strip()
    cfg["recs_col"] = str(collections["recommendations"]).strip()
    cfg["events_col"] = str(collections["events"]).strip()

    sa_info = fs.get("service_account")
    cfg["service_account"] = sa_info if isinstance(sa_info, dict) else None
    cfg["debug"] = bool(fs.get("debug"))
    return cfg


def _ts_ms() -> int:
    return int(time.time() * 1000)


class DDB:
    """Firestore-backed helper reusing the existing DDB interface.

    Collections used (names from env above):
    - Users: document id = user_email
    - Songs: document id = song_id
    - Recommendations: document id = user_email
    - Events: auto-id documents with fields {user_email, ts, event_type, payload}
    """

    def __init__(self, project_id: Optional[str] = None):
        # Load configuration from secrets
        cfg = _get_fs_config()
        project = project_id or cfg.get("project_id")
        sa_info = cfg.get("service_account")
        # Initialize Firestore client
        if sa_info:
            # If service account provided, use it directly
            self._client = firestore.Client.from_service_account_info(sa_info, project=project or sa_info.get("project_id"))
        else:
            # Use ADC with optional project id
            self._client = firestore.Client(project=project) if project else firestore.Client()
        # Collections
        self._users = self._client.collection(cfg["users_col"]) 
        self._songs = self._client.collection(cfg["songs_col"]) 
        self._recs = self._client.collection(cfg["recs_col"]) 
        self._events = self._client.collection(cfg["events_col"]) 
        # Debug flag
        self._debug = bool(cfg.get("debug"))

    # Users
    def upsert_user(self, email: str, name: str) -> bool:
        try:
            if not email:
                return False
            doc_ref = self._users.document(email)
            doc_ref.set({
                "user_email": email,
                "name": name or "User",
                "updated_at": _ts_ms(),
            }, merge=True)
            return True
        except GoogleAPIError as e:
            if self._debug:
                st.error(f"Firestore upsert_user failed: {e}")
            raise

    # Recommendations
    def put_recommendations(self, email: str, categories: List[Dict[str, Any]], cognitive_scores: Optional[Dict[str, Any]]) -> bool:
        try:
            if not email:
                return False
            data: Dict[str, Any] = {
                "user_email": email,
                "updated_at": _ts_ms(),
                "categories": categories or [],
            }
            if cognitive_scores is not None:
                data["cognitive_scores"] = cognitive_scores
            self._recs.document(email).set(data)
            return True
        except GoogleAPIError as e:
            if self._debug:
                st.error(f"Firestore put_recommendations failed: {e}")
            raise

    def get_recommendations(self, email: str) -> Optional[Dict[str, Any]]:
        try:
            if not email:
                return None
            snap = self._recs.document(email).get()
            return snap.to_dict() if snap.exists else None
        except GoogleAPIError as e:
            if self._debug:
                st.error(f"Firestore get_recommendations failed: {e}")
            raise

    # Events
    def log_event(self, email: str, event_type: str, payload: Optional[Dict[str, Any]] = None) -> bool:
        try:
            if not email:
                return False
            self._events.add({
                "user_email": email,
                "ts": _ts_ms(),
                "event_type": event_type,
                "payload": payload or {},
            })
            return True
        except GoogleAPIError as e:
            if self._debug:
                st.error(f"Firestore log_event failed: {e}")
            raise

    # Songs (optional placeholders)
    def put_song(self, song_id: str, data: Dict[str, Any]) -> bool:
        try:
            if not song_id:
                return False
            self._songs.document(song_id).set({"song_id": song_id, **data})
            return True
        except GoogleAPIError as e:
            if self._debug:
                st.error(f"Firestore put_song failed: {e}")
            raise

    def list_songs(self, category: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Return songs from Firestore; when category is provided, filter on it.
        Each item includes an 'id' key with the document ID.
        """
        try:
            query = self._songs
            if category:
                query = query.where('category', '==', category)
            stream = query.stream()
            items: List[Dict[str, Any]] = []
            for doc in stream:
                data = doc.to_dict() or {}
                data.setdefault('song_id', doc.id)
                data.setdefault('id', doc.id)
                items.append(data)
                if limit and len(items) >= limit:
                    break
            return items
        except GoogleAPIError as e:
            if self._debug:
                st.error(f"Firestore list_songs failed: {e}")
            raise

    def health_check(self) -> bool:
        """Attempt a lightweight operation to validate Firestore connectivity."""
        try:
            # Try a no-op read on users collection
            _ = self._users.limit(1).stream()
            for _doc in _:
                break
            return True
        except GoogleAPIError as e:
            if self._debug:
                st.error(f"Firestore health_check failed: {e}")
            return False

    # -----------------------------
    # Catalog seeding helpers
    # -----------------------------
    @staticmethod
    def _default_audio_url(category: str) -> str:
        urls = {
            "Classical": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
            "Rock": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3",
            "Pop": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3",
            "Rap": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-4.mp3",
            "R&B": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-5.mp3",
        }
        return urls.get(category, urls["Classical"]) 

    def seed_initial_songs(self) -> int:
        """Seed Firestore with a default catalog grouped by category.

        Fields per song: category, song_id, id, name, duration, bpm, key, url.
        Returns the number of songs successfully written.
        """
        catalog = {
            "Classical": [
                {"id": 1, "name": "Bach's Prelude", "duration": 240, "bpm": 72, "key": "C Major"},
                {"id": 2, "name": "Mozart's Sonata", "duration": 280, "bpm": 68, "key": "G Major"},
                {"id": 3, "name": "Beethoven's Symphony", "duration": 320, "bpm": 76, "key": "F Major"},
                {"id": 4, "name": "Chopin's Nocturne", "duration": 200, "bpm": 65, "key": "D Major"},
                {"id": 5, "name": "Vivaldi's Spring", "duration": 260, "bpm": 80, "key": "A Major"},
                {"id": 6, "name": "Debussy's Clair de Lune", "duration": 220, "bpm": 62, "key": "E Major"},
                {"id": 7, "name": "Pachelbel's Canon", "duration": 300, "bpm": 70, "key": "B♭ Major"},
                {"id": 8, "name": "Schubert's Ave Maria", "duration": 180, "bpm": 60, "key": "C Major"},
                {"id": 9, "name": "Brahms' Lullaby", "duration": 160, "bpm": 58, "key": "G Major"}
            ],
            "Rock": [
                {"id": 10, "name": "Thunder Strike", "duration": 210, "bpm": 140, "key": "E Minor"},
                {"id": 11, "name": "Electric Storm", "duration": 195, "bpm": 145, "key": "A Minor"},
                {"id": 12, "name": "Power Chord", "duration": 180, "bpm": 135, "key": "D Minor"},
                {"id": 13, "name": "Rock Anthem", "duration": 240, "bpm": 130, "key": "G Minor"},
                {"id": 14, "name": "Guitar Hero", "duration": 220, "bpm": 138, "key": "C Minor"},
                {"id": 15, "name": "Metal Fusion", "duration": 200, "bpm": 142, "key": "F Minor"},
                {"id": 16, "name": "Drum Solo", "duration": 160, "bpm": 150, "key": "B Minor"},
                {"id": 17, "name": "Bass Drop", "duration": 185, "bpm": 136, "key": "E Minor"},
                {"id": 18, "name": "Amplified", "duration": 205, "bpm": 144, "key": "A Minor"}
            ],
            "Pop": [
                {"id": 19, "name": "Catchy Beat", "duration": 180, "bpm": 120, "key": "C Major"},
                {"id": 20, "name": "Dance Floor", "duration": 200, "bpm": 125, "key": "G Major"},
                {"id": 21, "name": "Radio Hit", "duration": 190, "bpm": 118, "key": "F Major"},
                {"id": 22, "name": "Upbeat Melody", "duration": 175, "bpm": 122, "key": "D Major"},
                {"id": 23, "name": "Feel Good", "duration": 185, "bpm": 115, "key": "A Major"},
                {"id": 24, "name": "Summer Vibes", "duration": 195, "bpm": 128, "key": "E Major"},
                {"id": 25, "name": "Chart Topper", "duration": 170, "bpm": 120, "key": "B♭ Major"},
                {"id": 26, "name": "Mainstream", "duration": 188, "bpm": 124, "key": "C Major"},
                {"id": 27, "name": "Pop Anthem", "duration": 205, "bpm": 116, "key": "G Major"}
            ],
            "Rap": [
                {"id": 28, "name": "Street Beats", "duration": 200, "bpm": 95, "key": "E Minor"},
                {"id": 29, "name": "Urban Flow", "duration": 180, "bpm": 88, "key": "A Minor"},
                {"id": 30, "name": "Hip Hop Classic", "duration": 220, "bpm": 92, "key": "D Minor"},
                {"id": 31, "name": "Freestyle", "duration": 160, "bpm": 100, "key": "G Minor"},
                {"id": 32, "name": "Boom Bap", "duration": 195, "bpm": 85, "key": "C Minor"},
                {"id": 33, "name": "Trap Beat", "duration": 175, "bpm": 105, "key": "F Minor"},
                {"id": 34, "name": "Conscious Rap", "duration": 240, "bpm": 90, "key": "B Minor"},
                {"id": 35, "name": "Underground", "duration": 210, "bpm": 87, "key": "E Minor"},
                {"id": 36, "name": "Lyrical Flow", "duration": 185, "bpm": 93, "key": "A Minor"}
            ],
            "R&B": [
                {"id": 37, "name": "Smooth Soul", "duration": 220, "bpm": 75, "key": "C Major"},
                {"id": 38, "name": "Velvet Voice", "duration": 240, "bpm": 70, "key": "G Major"},
                {"id": 39, "name": "Groove Master", "duration": 200, "bpm": 78, "key": "F Major"},
                {"id": 40, "name": "Soulful Nights", "duration": 260, "bpm": 68, "key": "D Major"},
                {"id": 41, "name": "Love Ballad", "duration": 210, "bpm": 72, "key": "A Major"},
                {"id": 42, "name": "Midnight Groove", "duration": 195, "bpm": 76, "key": "E Major"},
                {"id": 43, "name": "Neo Soul", "duration": 225, "bpm": 74, "key": "B♭ Major"},
                {"id": 44, "name": "Rhythm & Blues", "duration": 250, "bpm": 65, "key": "C Major"},
                {"id": 45, "name": "Smooth Operator", "duration": 180, "bpm": 80, "key": "G Major"}
            ],
        }

        written = 0
        for category, tracks in catalog.items():
            for t in tracks:
                song_id = str(t["id"]).strip()
                payload = {
                    "name": t.get("name"),
                    "duration": t.get("duration"),
                    "bpm": t.get("bpm"),
                    "key": t.get("key"),
                    "category": category,
                    "url": self._default_audio_url(category),
                }
                if self.put_song(song_id, payload):
                    written += 1
        return written
