import streamlit as st
from typing import Dict, Any, Optional
from general_user import general_user_dashboard as music_therapy_dashboard
from caregiver import caregiver_dashboard as ml_caregiver_dashboard
import os
from db import DDB

# Configure Streamlit page
st.set_page_config(
    page_title="NeuroTunes",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded"
)

IMAGE_ADDRESS = "https://www.denvercenter.org/wp-content/uploads/2024/10/music-therapy.jpg"

# Caregiver emails (simple list)
CAREGIVER_EMAILS = [
    "vani.kandasamy@pyxeda.ai"
]

def is_caregiver(email: str) -> bool:
    return email.lower() in [e.lower() for e in CAREGIVER_EMAILS]

def get_user_simple() -> Optional[Dict[str, Any]]:
    """Get user via Streamlit auth."""
    # Check if authentication is available
    if not hasattr(st, 'user') or not st.user:
        st.warning("Please log in to continue.")
        return None
        
    # User is logged in
    with st.sidebar:
        if st.button("Log out", type="secondary"):
            st.session_state.clear()
            st.rerun()
            return None
            
    name = getattr(st.user, "name", None) or getattr(st.user, "username", None) or "User"
    email = getattr(st.user, "email", None) or ""
    
    st.markdown(f"Hello, <span style='color: orange; font-weight: bold;'>{name}</span>!", unsafe_allow_html=True)
    return {"name": name, "email": email}

def main():
    """Main application logic (simple auth + role routing)."""
    # Title and image
    st.title("NeuroTunes")
    st.image(IMAGE_ADDRESS, caption="EEG Frequency Bands (Delta, Theta, Alpha, Beta, Gamma)")
    st.markdown("---")

    # Authenticate
    user = get_user_simple()
    if not user:
        st.stop()
    st.session_state.user_info = user

    # Upsert user and log login to Firestore
    email = (user.get("email") or "").strip()
    name = (user.get("name") or "User").strip()
    if email:
        ddb = DDB()
        ok_user = ddb.upsert_user(email, name)
        ok_log = ddb.log_event(email, 'login', {})

    # One-time automatic seeding: if songs dataset is empty, seed defaults
    if not st.session_state.get("_seed_done"):
        try:
            ddb_seed = DDB()
            has_any = len(ddb_seed.list_songs(limit=1)) > 0
            if not has_any:
                _ = ddb_seed.seed_initial_songs()
        except Exception:
            pass
        finally:
            st.session_state["_seed_done"] = True

    # Route by role based on email
    user_email = (user.get("email") or "").strip()
    if user_email and is_caregiver(user_email):
        # Caregiver dashboard
        ml_caregiver_dashboard()
    else:
        # General user dashboard
        music_therapy_dashboard()

if __name__ == "__main__":
    main()