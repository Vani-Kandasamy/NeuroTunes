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
    "aiclubcolab@gmail.com"
]

def is_caregiver(email: str) -> bool:
    return email.lower() in [e.lower() for e in CAREGIVER_EMAILS]

def get_user_simple() -> Optional[Dict[str, Any]]:
    """Get user via Streamlit experimental auth if available; otherwise use a simple sidebar login form."""
    exp_user = getattr(st, "experimental_user", None)
    has_login = hasattr(st, "login") and hasattr(st, "logout")
    # Preferred path: experimental auth available
    if exp_user is not None and hasattr(exp_user, "is_logged_in") and has_login:
        with st.sidebar:
            if not exp_user.is_logged_in:
                if st.button("Log in with Google", type="primary"):
                    st.login()
                return None
            else:
                if st.button("Log out", type="secondary"):
                    st.logout()
                    return None
        name = getattr(exp_user, "name", None) or getattr(exp_user, "username", None) or "User"
        email = getattr(exp_user, "email", None) or ""
        st.markdown(f"Hello, <span style='color: orange; font-weight: bold;'>{name}</span>!", unsafe_allow_html=True)
        return {"name": name, "email": email}
    
    # Fallback: simple form-based login stored in session_state
    with st.sidebar:
        st.info("Using simple sign-in (experimental auth not available).")
        if "simple_user" not in st.session_state:
            st.session_state.simple_user = None
        with st.form("simple_login_form", clear_on_submit=False):
            name = st.text_input("Name", value=(st.session_state.simple_user or {}).get("name", ""))
            email = st.text_input("Email (optional)", value=(st.session_state.simple_user or {}).get("email", ""))
            submitted = st.form_submit_button("Continue", type="primary")
        if submitted:
            st.session_state.simple_user = {"name": name.strip() or "User", "email": (email or "").strip()}
        user = st.session_state.simple_user
    if not user:
        return None
    st.markdown(f"Hello, <span style='color: orange; font-weight: bold;'>{user['name']}</span>!", unsafe_allow_html=True)
    return user



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

    # Upsert user and log login to DynamoDB (best-effort)
    try:
        email = (user.get("email") or "").strip()
        name = (user.get("name") or "User").strip()
        if email:
            ddb = DDB()
            ddb.upsert_user(email, name)
            ddb.log_event(email, 'login', {})
    except Exception:
        pass

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
