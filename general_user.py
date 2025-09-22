import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from typing import Dict, List, Optional, Any
from db import DDB

# Default categories for new users
DEFAULT_CATEGORIES = ["Classical", "Rock", "Pop", "Rap", "R&B"]

# Lazy-loaded catalog
CATALOG = {}

def _load_catalog_from_store() -> Dict[str, List[Dict[str, Any]]]:
    """Load and organize songs from Firestore by category."""
    try:
        by_cat = {cat: [] for cat in DEFAULT_CATEGORIES}
        by_cat["Uncategorized"] = []
        
        for item in DDB().list_songs() or []:
            cat = (item.get('category') or 'Uncategorized').strip()
            if cat not in by_cat:
                by_cat[cat] = []
            if 'id' not in item and 'song_id' in item:
                item['id'] = item['song_id']
            if 'id' in item:
                by_cat[cat].append(item)
        return {k: v for k, v in by_cat.items() if v}
    except Exception as e:
        st.warning("Unable to load songs. Please try again later.")
        return {}

def get_catalog() -> Dict[str, List[Dict[str, Any]]]:
    """Return cached catalog, loading from store on first access."""
    global CATALOG
    if not CATALOG:
        CATALOG = _load_catalog_from_store()
    return CATALOG

def initialize_session_state():
    """Initialize session state variables."""
    defaults = {
        'current_track': None,
        'is_playing': False,
        'playback_position': 0,
        'listening_history': [],
        'user_preferences': {
            'volume': 50,
            'preferred_categories': DEFAULT_CATEGORIES[:2]
        },
        'login_sessions': [],
        'session_started': False,
        'neural_data': pd.DataFrame()
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def get_caregiver_scores(email: str) -> Optional[Dict[str, float]]:
    """Retrieve caregiver-provided cognitive scores for a user."""
    if not email:
        return None
    
    try:
        entry = DDB().get_recommendations(email)
        if isinstance(entry, dict):
            scores = entry.get('cognitive_scores')
            if isinstance(scores, dict):
                return scores
    except Exception:
        pass
    return None

def get_recommended_playlist(email: str, max_tracks: int = 6) -> List[Dict[str, Any]]:
    """Generate a playlist based on caregiver recommendations."""
    if not email:
        return []
    
    try:
        entry = DDB().get_recommendations(email)
        if not isinstance(entry, dict):
            return []
            
        catalog = get_catalog()
        ranked = []
        
        # Process and normalize category scores
        for r in (entry.get('categories') or []):
            cat = str(r.get('category', '')).strip()
            if cat in catalog:
                score = float(r.get('score', 0.0))
                if score > 0:
                    ranked.append((cat, score))
        
        if not ranked:
            return []
            
        # Sort by score and allocate tracks
        ranked.sort(key=lambda x: -x[1])
        total = sum(score for _, score in ranked)
        if total <= 0:
            return []
            
        # Allocate tracks proportionally
        playlist = []
        remaining = max_tracks
        
        for cat, score in ranked:
            if remaining <= 0:
                break
                
            # Calculate number of tracks for this category
            count = max(1, min(remaining, int(round(score / total * max_tracks))))
            count = min(count, len(catalog[cat]), remaining)
            
            # Add tracks to playlist
            playlist.extend([
                {**track, 'category': cat} 
                for track in catalog[cat][:count]
            ])
            remaining -= count
            
        return playlist[:max_tracks]
        
    except Exception as e:
        if st.session_state.get('debug', False):
            st.error(f"Error generating playlist: {e}")
        return []

def _log_play_event(track: Dict[str, Any], category: str):
    """Log a play event to the database."""
    user_email = st.session_state.get('user_info', {}).get('email', '')
    if user_email and track and 'id' in track:
        DDB().log_event(user_email, 'play', {
            'track_id': track['id'],
            'name': track.get('name', ''),
            'category': category
        })

def music_player_widget(track: Dict[str, Any]):
    """Render an audio player for the given track."""
    if not track:
        return
        
    st.write(f"**{track.get('name', 'Unknown Track')}**")
    
    # Format duration (in seconds) to MM:SS
    duration = int(track.get('duration', 0))
    duration_str = f"{duration//60}:{duration%60:02d}"
    
    # Display track metadata
    meta = [
        f"Duration: {duration_str}" if duration else None,
        f"BPM: {track['bpm']}" if track.get('bpm') else None,
        f"Key: {track['key']}" if track.get('key') else None
    ]
    st.caption(" • ".join(filter(None, meta)))
    
    # Audio player
    if track.get('url'):
        st.audio(track['url'], format="audio/mp3")
    else:
        st.warning("No audio URL available for this track.")

def track_card(track: Dict[str, Any], category: str):
    """Render a track card with play button and metadata."""
    if not track:
        return
        
    with st.container():
        cols = st.columns([1, 4, 1])
        
        # Play button
        with cols[0]:
            if st.button("▶️", key=f"play_{track['id']}"):
                current = st.session_state.current_track
                if not current or current.get('id') != track.get('id'):
                    st.session_state.current_track = {**track, 'category': category}
                    st.session_state.is_playing = True
                    st.session_state.playback_position = 0
                    
                    # Add to listening history
                    st.session_state.listening_history.append({
                        'timestamp': datetime.now(),
                        'track': track,
                        'category': category
                    })
                    
                    # Log the play event
                    _log_play_event(track, category)
        
        # Track info
        with cols[1]:
            st.markdown(f"""
                **{track.get('name', 'Unknown Track')}**  
                Category: {category} | 
                Duration: {int(track.get('duration', 0))//60}:{int(track.get('duration', 0))%60:02d} | 
                BPM: {track.get('bpm', 'N/A')}  
                Key: {track.get('key', 'N/A')}
            """)
            
            # Show audio player if this is the current track
            current = st.session_state.current_track
            if current and current.get('id') == track.get('id'):
                music_player_widget(current)
        
        # Empty column for layout
        with cols[2]:
            st.empty()

def _render_dashboard():
    """Render the main dashboard view."""
    catalog = get_catalog()
    user_info = st.session_state.get('user_info', {})
    
    # Record login session if not already done
    if not st.session_state.session_started:
        st.session_state.login_sessions.append(datetime.now())
        st.session_state.session_started = True
        
        # Log login event
        email = user_info.get('email', '')
        if email:
            DDB().log_event(email, 'login', {})
            DDB().upsert_user(email, user_info.get('name', 'User'))
    
    # Now Playing section
    if st.session_state.current_track:
        st.subheader("🎵 Now Playing")
        music_player_widget(st.session_state.current_track)
        st.markdown("---")
    
    # Session info and recommendations
    col1, col2 = st.columns(2)
    
    with col1:
        # Caregiver recommendations
        email = user_info.get('email', '')
        scores = get_caregiver_scores(email)
        recommendations = get_recommended_playlist(email)
        
        if scores or recommendations:
            st.subheader("🩺 Recommended by Caregiver")
            
            # Display scores if available
            if scores:
                cols = st.columns(3)
                metrics = [
                    ('Engagement', 'engagement'),
                    ('Focus', 'focus'),
                    ('Relaxation', 'relaxation')
                ]
                
                for (label, key), col in zip(metrics, cols):
                    if key in scores and scores[key] is not None:
                        col.metric(label, f"{scores[key]:.1f}/10")
                
                st.markdown("---")
            
            # Display recommended tracks
            if recommendations:
                for track in recommendations:
                    track_card(track, track.get('category', 'Uncategorized'))
                st.markdown("---")
        
        # Featured tracks
        st.subheader("🌟 Featured Tracks")
        for cat in list(catalog.keys())[:2]:
            st.markdown(f"#### {cat}")
            for track in catalog.get(cat, [])[:2]:
                track_card(track, cat)
    
    with col2:
        st.subheader("🎯 Tips")
        st.info("""
            - Explore different music categories to find what works best for you
            - Try listening to recommended tracks from your caregiver
            - Take breaks between listening sessions for optimal results
        """)

def _render_music_library():
    """Render the music library view."""
    catalog = get_catalog()
    
    # Category filter
    available_categories = sorted(catalog.keys())
    selected_categories = st.multiselect(
        "Filter by Category",
        available_categories,
        default=available_categories[:2]
    )
    
    # Search
    search_term = st.text_input("🔍 Search tracks", "")
    search_lower = search_term.lower().strip()
    
    # Display tracks
    if not catalog:
        st.info("No songs available. Please check back later.")
        return
    
    for category in selected_categories:
        tracks = catalog.get(category, [])
        
        # Apply search filter
        if search_term:
            tracks = [
                t for t in tracks 
                if search_lower in t.get('name', '').lower()
            ]
        
        if not tracks:
            continue
            
        st.markdown(f"### {category} 🎵")
        for track in tracks:
            track_card(track, category)
        
        st.markdown("---")

def _render_trend_analysis():
    """Render the trend analysis view."""
    history = st.session_state.get('listening_history', [])
    
    if not history:
        st.info("No listening activity yet. Play some tracks to see your trends!")
        return
    
    # Convert to DataFrame for analysis
    df = pd.DataFrame([{
        'timestamp': h.get('timestamp'),
        'track_name': h.get('track', {}).get('name', 'Unknown'),
        'category': h.get('category', 'Uncategorized'),
        'duration': h.get('track', {}).get('duration', 0)
    } for h in history])
    
    # Top tracks this session
    if not df.empty:
        st.subheader("🌟 Top Tracks This Session")
        top_tracks = df['track_name'].value_counts().head(3)
        
        for track, count in top_tracks.items():
            st.metric(f"{track}", f"Played {count} times")
        
        st.markdown("---")
    
    # Category distribution
    if 'category' in df.columns:
        st.subheader("📊 Category Distribution")
        cat_counts = df['category'].value_counts()
        
        if not cat_counts.empty:
            fig = px.pie(
                names=cat_counts.index,
                values=cat_counts.values,
                title='Plays by Category'
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # Listening history timeline
    if 'timestamp' in df.columns:
        st.subheader("⏱️ Listening History")
        
        # Group by date and count plays
        df['date'] = pd.to_datetime(df['timestamp']).dt.date
        timeline = df.groupby('date').size().reset_index(name='plays')
        
        if not timeline.empty:
            fig = px.line(
                timeline,
                x='date',
                y='plays',
                title='Daily Plays',
                labels={'date': 'Date', 'plays': 'Number of Plays'}
            )
            st.plotly_chart(fig, use_container_width=True)

def general_user_dashboard():
    """Main entry point for the general user dashboard."""
    initialize_session_state()
    
    # Page title and welcome message
    user_name = st.session_state.get('user_info', {}).get('name', 'User')
    st.title("🎵 Music Therapy Portal")
    st.markdown(f"Welcome, **{user_name}**! Discover music for cognitive enhancement.")
    
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
        current = st.session_state.current_track
        if current:
            st.markdown(f"**Now Playing:** {current.get('name', 'Unknown')}")
        
        # Stop button
        if st.button("⏹️ Stop", use_container_width=True):
            if st.session_state.get('current_track'):
                # Log stop event
                email = st.session_state.get('user_info', {}).get('email', '')
                current = st.session_state.current_track
                if email and current:
                    try:
                        DDB().log_event(email, 'stop', {
                            'track_id': current.get('id'),
                            'name': current.get('name')
                        })
                    except Exception as e:
                        st.error(f"Error logging stop event: {str(e)}")
                
                # Reset player state
                st.session_state.current_track = None
                st.session_state.is_playing = False
                st.session_state.playback_position = 0
                
                # Force UI update
                st.rerun()
    
    # Main content area
    if page == "Dashboard":
        _render_dashboard()
    elif page == "Music Library":
        _render_music_library()
    elif page == "Trend Analysis":
        _render_trend_analysis()

# This allows the file to be imported without running the dashboard
if __name__ == "__main__":
    # Initialize session state if running this file directly
    if 'user_info' not in st.session_state:
        st.session_state.user_info = {'name': 'Test User', 'email': 'test@example.com'}
    general_user_dashboard()
