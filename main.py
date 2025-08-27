import streamlit as st
from typing import Dict, Any, Optional
from general_user import general_user_dashboard as music_therapy_dashboard
from caregiver import caregiver_dashboard as ml_caregiver_dashboard
import os
from db import DDB, get_firestore_client

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
    
    # No fallback: require Streamlit experimental auth
    return None



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
        # Save compact status for Admin diagnostics panel
        try:
            st.session_state["_login_fs_status"] = {
                "ok_user": bool(ok_user),
                "ok_log": bool(ok_log),
                "last_error": ddb.last_error(),
            }
        except Exception:
            st.session_state["_login_fs_status"] = {
                "ok_user": bool(ok_user),
                "ok_log": bool(ok_log),
                "last_error": None,
            }

    # Admin tools (optional): enable via .streamlit/secrets.toml -> [admin] enable = true
    try:
        admin_enabled = bool((st.secrets.get("admin", {}) or {}).get("enable")) or bool(st.secrets.get("FIRESTORE_ADMIN"))
    except Exception:
        admin_enabled = False
    if admin_enabled:
        with st.sidebar.expander("🛠️ Admin", expanded=False):
            # Temporary debugging: secrets visibility
            if st.checkbox("Show Secrets Debug", value=False):
                try:
                    st.write("Secrets keys:", list(st.secrets.keys()))
                    # Neutral checks (no dependence on 'firestore' section)
                    st.write("Has gcp_service_account:", "gcp_service_account" in st.secrets)
                    st.write("Has [collections] mapping:", isinstance(st.secrets.get("collections"), dict))
                except Exception as e:
                    st.error(f"Unable to read secrets: {e}")
            # Firestore login write status
            fs_stat = st.session_state.get("_login_fs_status")
            if fs_stat:
                if fs_stat["ok_user"] and fs_stat["ok_log"]:
                    st.caption("Login recorded in Firestore.")
                else:
                    st.warning("Firestore write failed for login upsert/event.")
                    if fs_stat.get("last_error"):
                        st.caption(f"Last Firestore error: {fs_stat['last_error']}")
            if st.button("Health Check: Firestore"):
                try:
                    ok = DDB().health_check()
                    if ok:
                        st.success("Firestore health OK ✔️")
                    else:
                        st.error("Firestore health check failed ❌")
                except Exception as e:
                    st.error(f"Health check error: {e}")
            # Raw Firestore write test using get_firestore_client()
            if st.button("Raw Firestore Write (test)"):
                try:
                    db = get_firestore_client()
                    doc_ref = db.collection("NeuroTunes_Users").document("user@example.com")
                    doc_ref.set({"user_email": "user@example.com"})
                    st.success("Raw write succeeded: NeuroTunes_Users/user@example.com")
                except Exception as e:
                    st.error(f"Raw write failed: {e}")
            if st.button("Seed Default Songs"):
                try:
                    count = DDB().seed_initial_songs()
                    st.success(f"Seeded {count} songs into Firestore ✔️")
                except Exception as e:
                    st.error(f"Seeding failed: {e}")

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
