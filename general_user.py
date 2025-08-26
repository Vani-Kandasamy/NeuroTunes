import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import json
from pathlib import Path

# Melody database with 5 music genres (neural score removed)
MELODY_DATABASE = {
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
    ]
}

def get_audio_url(category: str) -> str:
    """Return a placeholder audio URL per category for testing playback in the browser."""
    urls = {
        "Classical": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
        "Rock": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3",
        "Pop": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3",
        "Rap": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-4.mp3",
        "R&B": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-5.mp3",
    }
    return urls.get(category, "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3")

def attach_audio_urls_to_database():
    """Populate each track with a genre-specific 'url' using provided placeholders."""
    for category, tracks in MELODY_DATABASE.items():
        cat_url = get_audio_url(category)
        for t in tracks:
            t['url'] = cat_url

# Attach URLs at import time
attach_audio_urls_to_database()

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
    data = _read_caregiver_recommendations()
    entry = data.get(user_email)
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
        if str(r.get('category')) in MELODY_DATABASE
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
        for track in MELODY_DATABASE.get(cat, [])[:cnt]:
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
    
    # Record a login session timestamp once per app session
    if not st.session_state.session_started:
        st.session_state.login_sessions.append(datetime.now())
        st.session_state.session_started = True
    
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
        
        st.markdown("---")
        if st.button("🚪 Sign Out", use_container_width=True):
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
            for cat in list(MELODY_DATABASE.keys())[:2]:
                st.markdown(f"#### {cat}")
                for track in MELODY_DATABASE[cat][:2]:
                    track_card(track, cat)
        
        with col2:
            st.subheader("🎯 Tips")
            st.info("Explore categories in the Music Library and pick what you enjoy. Neural and engagement scores are no longer shown.")
    
    elif page == "Music Library":
        st.subheader("🎼 Music Library")
        
        # Category filter
        selected_categories = st.multiselect(
            "Filter by Category",
            ["Classical", "Rock", "Pop", "Rap", "R&B"],
            default=["Classical", "Rock", "Pop", "Rap", "R&B"]
        )
        
        # Search
        search_term = st.text_input("🔍 Search tracks", placeholder="Enter track name...")
        
        # Display tracks by category
        for category in selected_categories:
            if category in MELODY_DATABASE:
                st.markdown(f"### {category} 🎵")
                
                tracks = MELODY_DATABASE[category]
                
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
