import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import json
from pathlib import Path
from db import DDB

def _load_catalog_from_store() -> dict:
    """Load songs from Firestore and group by category. Ensure id and url fields."""
    by_cat = {}
    try:
        ddb = DDB()
        items = ddb.list_songs()
        for it in items:
            cat = it.get('category') or 'Uncategorized'
            # Normalize id and url
            song_id = it.get('id') or it.get('song_id')
            if song_id is None:
                continue
            it['id'] = song_id
            by_cat.setdefault(cat, []).append(it)
    except Exception:
        return {}
    return by_cat

# Global catalog loaded at import
CATALOG = _load_catalog_from_store()

def initialize_session_state():
    """Initialize session state variables"""
    if 'current_track' not in st.session_state:
        st.session_state.current_track = None
    if 'is_playing' not in st.session_state:
        st.session_state.is_playing = False
    if 'playback_position' not in st.session_state:
        st.session_state.playback_position = 0
    if 'listening_history' not in st.session_state:
        st.session_state.listening_history = []
    # Neural engagement data removed; keep placeholder for compatibility if referenced
    if 'neural_data' not in st.session_state:
        st.session_state.neural_data = pd.DataFrame()
    if 'user_preferences' not in st.session_state:
        st.session_state.user_preferences = {"volume": 50, "preferred_categories": ["Classical"]}
    # Login session tracking
    if 'login_sessions' not in st.session_state:
        st.session_state.login_sessions = []  # list[datetime]
    if 'session_started' not in st.session_state:
        st.session_state.session_started = False

# Sample neural data generation removed

def _read_caregiver_recommendations() -> dict:
    """Read shared recommendations file written by caregiver dashboard."""
    rec_path = Path(__file__).parent / "shared_recommendations.json"
    try:
        if rec_path.exists():
            with open(rec_path, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def get_caregiver_scores_for_user(user_email: str):
    """Return caregiver-provided cognitive scores dict for this user if available."""
    if not user_email:
        return None
    # Prefer DynamoDB if available
    try:
        ddb = DDB()
        item = ddb.get_recommendations(user_email)
        if item:
            entry = item
        else:
            entry = _read_caregiver_recommendations().get(user_email)
    except Exception:
        entry = _read_caregiver_recommendations().get(user_email)
    if not entry or not isinstance(entry, dict):
        return None
    scores = entry.get('cognitive_scores')
    if not isinstance(scores, dict):
        return None
    return scores

def get_recommended_playlist_for_user(user_email: str, max_tracks: int = 6):
    """Build a playlist based on caregiver category rankings for this user.

    Strategy: take categories ranked by caregiver and pick up to ceil(weight*max_tracks)
    tracks from each category (at least 1), preserving database order.
    """
    if not user_email:
        return []
    data = _read_caregiver_recommendations()
    entry = data.get(user_email)
    if not entry or not isinstance(entry, dict):
        return []
    ranked = entry.get('categories') or []
    if not ranked:
        return []
    # Normalize scores
    total = float(sum((r.get('score') or 0.0) for r in ranked)) or 1.0
    ranked = [
        {
            'category': str(r.get('category')),
            'score': float((r.get('score') or 0.0) / total)
        }
        for r in ranked
        if str(r.get('category')) in CATALOG
    ]
    # Allocate tracks per category
    import math
    alloc = []
    remaining = max_tracks
    for i, r in enumerate(ranked):
        count = max(1, int(round(r['score'] * max_tracks)))
        # Ensure we don't exceed remaining
        if i == len(ranked) - 1:
            count = max(1, remaining)
        count = min(count, remaining)
        alloc.append((r['category'], count))
        remaining -= count
        if remaining <= 0:
            break
    # Build list of track dicts with category attached
    playlist = []
    for cat, cnt in alloc:
        for track in CATALOG.get(cat, [])[:cnt]:
            # Attach category and URL for playback
            playlist.append({**track, 'category': cat})
            if len(playlist) >= max_tracks:
                break
        if len(playlist) >= max_tracks:
            break
    return playlist

def music_player_widget(track):
    """Create a music player widget with real audio playback."""
    if track:
        # Basic info
        st.write(f"**{track['name']}**")
        st.caption(f"Duration: {track['duration']//60}:{track['duration']%60:02d} • BPM: {track['bpm']}")

        # Play only if the track has an explicit URL configured
        audio_url = track.get('url')
        if audio_url:
            st.audio(audio_url, format="audio/mp3")
        else:
            st.warning("No audio URL configured for this track yet. Please add a URL to play.")

def track_card(track, category):
    """Create a track card with play button and details"""
    with st.container():
        col1, col2, col3 = st.columns([1, 4, 1])
        
        with col1:
            if st.button("▶️", key=f"card_play_{track['id']}"):
                # Attach category to track so the audio URL can be resolved
                st.session_state.current_track = {**track, 'category': category}
                st.session_state.is_playing = True
                st.session_state.playback_position = 0
                
                # Add to listening history
                st.session_state.listening_history.append({
                    'timestamp': datetime.now(),
                    'track': track,
                    'category': category
                })
                # Log play event to DynamoDB
                try:
                    user_email = (st.session_state.get('user_info', {}) or {}).get('email', '')
                    DDB().log_event(user_email, 'play', {
                        'track_id': track.get('id'),
                        'name': track.get('name'),
                        'category': category,
                    })
                except Exception:
                    pass
        
        with col2:
            st.markdown(f"""
            **{track['name']}**  
            Category: {category} | Duration: {track['duration']//60}:{track['duration']%60:02d} | BPM: {track['bpm']}  
            Key: {track['key']}
            """)
            # If this track is currently selected, render the audio player here
            if st.session_state.current_track and st.session_state.current_track.get('id') == track['id']:
                music_player_widget(st.session_state.current_track)
        
        with col3:
            st.empty()


def general_user_dashboard():
    """Main dashboard for general users with music therapy features"""
    initialize_session_state()
    
    user_info = st.session_state.user_info
    
    st.title("🎵 Music Therapy Portal")
    st.markdown(f"Welcome, **{user_info['name']}**! Discover your optimal melodies for cognitive enhancement.")
    
    # Record a login session timestamp once per app session and log to DDB
    if not st.session_state.session_started:
        st.session_state.login_sessions.append(datetime.now())
        st.session_state.session_started = True
        try:
            user_email = (st.session_state.get('user_info', {}) or {}).get('email', '')
            user_name = (st.session_state.get('user_info', {}) or {}).get('name', 'User')
            ddb = DDB()
            ddb.log_event(user_email, 'login', {})
            ddb.upsert_user(user_email, user_name)
        except Exception:
            pass
    
    # Sidebar navigation
    with st.sidebar:
        st.markdown("### 🎼 Navigation")
        page = st.selectbox(
            "Select Feature",
            ["Dashboard", "Music Library", "Trend Analysis"]
        )
        
        st.markdown("---")
        st.markdown("### 🎛️ Quick Controls")
        
        # Current track display
        if st.session_state.current_track:
            st.markdown("**Now Playing:**")
            st.write(st.session_state.current_track['name'])
        
        # Playback control
        if st.button("⏹️ Stop", use_container_width=True):
            st.session_state.current_track = None
            st.session_state.is_playing = False
            st.session_state.playback_position = 0
            # Log stop event to DynamoDB
            try:
                user_email = (st.session_state.get('user_info', {}) or {}).get('email', '')
                DDB().log_event(user_email, 'stop', {})
            except Exception:
                pass
        
        st.markdown("---")
        if st.button("🚪 Sign Out", use_container_width=True):
            # Log logout event
            try:
                user_email = (st.session_state.get('user_info', {}) or {}).get('email', '')
                DDB().log_event(user_email, 'logout', {})
            except Exception:
                pass
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    # Main content
    if page == "Dashboard":
        # Music player section
        if st.session_state.current_track:
            st.subheader("🎵 Now Playing")
            music_player_widget(st.session_state.current_track)
            st.markdown("---")
        
        # Removed neural engagement statistics from Dashboard
        
        # Session activity summary
        sessions = len(st.session_state.get('login_sessions', []))
        if sessions:
            st.markdown("### 👤 Session Activity")
            c1, c2 = st.columns(2)
            with c1:
                st.metric("Login Sessions", sessions)
            with c2:
                st.caption(f"Last login: {st.session_state['login_sessions'][-1].strftime('%Y-%m-%d %H:%M')}")
        
        # Caregiver-linked recommendations and featured tracks
        col1, col2 = st.columns(2)
        
        with col1:
            # Recommended by caregiver (if any)
            user_email = (st.session_state.get('user_info', {}) or {}).get('email', '')
            # Show caregiver-provided cognitive scores if present
            scores = get_caregiver_scores_for_user(user_email)
            rec_playlist = get_recommended_playlist_for_user(user_email)
            if scores or rec_playlist:
                st.subheader("🩺 Recommended by Caregiver")
            if scores:
                c1, c2, c3 = st.columns(3)
                with c1:
                    val = scores.get('engagement')
                    if val is not None:
                        st.metric("Engagement", f"{val:.1f}/10")
                with c2:
                    val = scores.get('focus')
                    if val is not None:
                        st.metric("Focus", f"{val:.1f}/10")
                with c3:
                    val = scores.get('relaxation')
                    if val is not None:
                        st.metric("Relaxation", f"{val:.1f}/10")
                st.markdown("---")
            if rec_playlist:
                for track in rec_playlist:
                    track_card(track, track['category'])
                st.markdown("---")
            st.subheader("🌟 Featured Tracks")
            # Show a few tracks from each category
            for cat in list(CATALOG.keys())[:2]:
                st.markdown(f"#### {cat}")
                for track in CATALOG.get(cat, [])[:2]:
                    track_card(track, cat)
        
        with col2:
            st.subheader("🎯 Tips")
            st.info("Explore categories in the Music Library and pick what you enjoy. Neural and engagement scores are no longer shown.")
    
    elif page == "Music Library":
        st.subheader("🎼 Music Library")
        
        # Category filter
        available_categories = sorted(list(CATALOG.keys()))
        selected_categories = st.multiselect(
            "Filter by Category",
            available_categories,
            default=available_categories
        )
        
        # Search
        search_term = st.text_input("🔍 Search tracks", placeholder="Enter track name...")
        
        # Display tracks by category
        if not CATALOG:
            st.info("No songs available. Please add songs to Firestore.")
        for category in selected_categories:
            if category in CATALOG:
                st.markdown(f"### {category} 🎵")
                
                tracks = CATALOG.get(category, [])
                
                # Filter by search term
                if search_term:
                    tracks = [t for t in tracks if search_term.lower() in t['name'].lower()]
                
                if tracks:
                    for track in tracks:
                        track_card(track, category)
                else:
                    st.info(f"No tracks found matching '{search_term}' in {category} category.")
                
                st.markdown("---")
    
    # 'My Playlists' page removed per request; keep route disabled for safety
    elif False and page == "My Playlists":
        st.subheader("🎵 Smart Playlists")
        
        df = st.session_state.neural_data
        
        if not df.empty:
            # Find user's top track
            top_track_data = df.loc[df['neural_engagement'].idxmax()]
            top_track = None
            
            # Find the actual track object
            for category, tracks in MELODY_DATABASE.items():
                for track in tracks:
                    if track['id'] == top_track_data['track_id']:
                        top_track = track
                        break
            
            if top_track:
                st.markdown(f"### 🌟 Based on your top track: **{top_track['name']}**")
                st.markdown(f"Neural Engagement Score: **{top_track_data['neural_engagement']:.1f}/10**")
                
                st.markdown("### 🎼 Recommended Playlist")
                st.info("Playlist recommendations are temporarily disabled.")
        else:
            st.info("Listen to some tracks first to generate personalized playlists!")
    
    # Neural Analytics page removed
    
    elif page == "Trend Analysis":
        st.subheader("📈 Trend Analysis")
        
        # Show music categories listened so far
        history = st.session_state.get('listening_history', [])
        if history:
            st.markdown("---")
            st.markdown("### 🎧 Category Listening Summary")
            hist_df = pd.DataFrame(history)
            # Ensure timestamp column is datetime
            if 'timestamp' in hist_df.columns:
                hist_df['timestamp'] = pd.to_datetime(hist_df['timestamp'], errors='coerce')
            
            # Category distribution (counts)
            if 'category' in hist_df.columns and not hist_df['category'].isna().all():
                cat_counts = hist_df['category'].value_counts().sort_values(ascending=False)
                fig_cat = px.bar(
                    x=cat_counts.index,
                    y=cat_counts.values,
                    labels={'x': 'Category', 'y': 'Play Count'},
                    title='Plays by Category'
                )
                st.plotly_chart(fig_cat, use_container_width=True)
            else:
                st.info("No category information found in listening history.")

            # Daily timeline removed per request
        else:
            st.info("No listening activity yet. Play some tracks to see your category trends here.")
    
    # 'Export Report' removed per request; route disabled
    elif False and page == "Export Report":
        export_report()
