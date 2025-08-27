# Healthcare Portal - Music Therapy App with Google Sign-In

A Streamlit web application with Google OAuth authentication that routes users to different dashboards based on their email addresses. Features an advanced music therapy system for general users with neural engagement tracking.

## Features

- **Google OAuth Authentication**: Secure login with Google accounts
- **Role-based Access Control**: Different interfaces for caregivers and general users
- **Caregiver Dashboard**: Patient management, appointments, reports, and settings
- **Music Therapy Portal**: Advanced music therapy system for general users
- **Email-based Routing**: Automatic redirection based on user email domain

### Music Therapy Features (General Users)
- **Melody Database**: 45+ curated melodies across 5 music genres (Classical, Rock, Pop, Rap, R&B)
- **Interactive Music Player**: Play/pause controls, progress bars, volume sliders
- **Neural Engagement Tracking**: Monitor brain response to different melodies
- **Smart Playlist Generation**: AI-powered recommendations based on highest engagement scores
- **Visual Analytics**: Charts and graphs showing listening patterns and neural engagement
- **Trend Analysis**: Time-based patterns, weekly trends, and completion rates
- **Export Reports**: Download detailed analytics in JSON or CSV format
- **Genre-based Organization**: Browse music by therapeutic music genres

### ML-Powered Caregiver Features
- **Pre-trained Random Forest Model**: Uses default trained model for music genre predictions (Classical, Rock, Pop, Rap, R&B)
- **Patient-Specific EEG Data Management**: Upload and manage EEG data for individual patients
- **EEG Data Processing**: Automated analysis of brain wave frequency bands (Delta, Theta, Alpha, Beta, Gamma)
- **Cognitive Score Calculations**:
  - **Engagement Score**: `Mean(Beta+Gamma) - Mean(Alpha+Theta)` - measures mental alertness
  - **Focus Score**: `Theta/Beta Ratio` - measures sustained attention and concentration
  - **Relaxation Score**: `Mean(Alpha+Theta) - Mean(Beta+Gamma)` - measures calmness and passive mental states
- **Multi-Patient Support**: Manage data for multiple patients with individual tracking
- **Patient Selection Interface**: Choose existing patients or create new patient profiles
- **ML Model Performance Dashboard**: View model accuracy, capabilities, and performance metrics
- **Cognitive Insights Visualization**: Interactive charts showing brain response patterns per patient
- **Real EEG Data Upload**: CSV import functionality for authentic EEG datasets (no synthetic data)
- **Patient Summary Dashboard**: Overview of all patients with average cognitive scores
- **Comprehensive Reporting**: Export detailed patient analysis and ML predictions

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google+ API
4. Create OAuth 2.0 credentials:
   - Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client IDs"
   - Choose "Web application"
   - Add authorized origins (e.g., `http://localhost:8501`)
   - Add authorized redirect URIs (e.g., `http://localhost:8501`)

### 3. Streamlit Secrets Configuration (Required)

Create `.streamlit/secrets.toml` with Google OAuth and Firestore settings. Experimental auth is required; no simple fallback login exists.

```toml
[default]
GOOGLE_CLIENT_ID = "your-actual-client-id.apps.googleusercontent.com"

[firestore]
project_id = "your-gcp-project-id"
debug = true  # optional

[firestore.collections]
users = "NeuroTunes_Users"
songs = "NeuroTunes_Songs"
recommendations = "NeuroTunes_Recommendations"
events = "NeuroTunes_Events"

# Optional: for local/dev use a service account instead of ADC
[firestore.service_account]
type = "service_account"
project_id = "your-gcp-project-id"
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "svc@your-gcp-project-id.iam.gserviceaccount.com"
token_uri = "https://oauth2.googleapis.com/token"
```

Add `.streamlit/secrets.toml` to your `.gitignore` file to keep credentials secure.

### 4. Configure Caregiver Emails

Edit the `CAREGIVER_EMAILS` list in `main.py` to include the email addresses that should have caregiver access:

```python
CAREGIVER_EMAILS = [
    "doctor@hospital.com",
    "nurse@healthcare.com",
    "admin@clinic.com",
    # Add more caregiver emails here
]
```

## Running the Application

```bash
streamlit run main.py
```

The app will be available at `http://localhost:8501`

## Required Files

### Pre-trained ML Model
Place a pre-trained Random Forest model file named `best_RF_with_time` (no extension) in the project root directory. This model should be trained to predict music genres (1=Classical, 2=Rock, 3=Pop, 4=Rap, 5=R&B) from EEG frequency band features.

### EEG Data Format
For caregiver uploads, CSV files should contain:
- **40 EEG columns**: Frequency bands (Delta, Theta, Alpha, Beta, Gamma) for 4 electrodes (TP9, AF7, AF8, TP10)
- **Format**: `{Band}_{Electrode}_mean` (e.g., `Delta_TP9_mean`, `Alpha_AF7_mean`)
- **Target column**: `Melody #` (1-5 for music genres)
- **No metadata**: Patient ID assigned automatically during upload

## Authentication

The app uses Streamlit experimental auth (Google Sign-In). If experimental auth is unavailable or the user is not logged in, the app will not proceed past the login screen.

## User Roles

### Caregivers
- **ML-Powered Analytics**: Access to Random Forest model for music therapy predictions
- **Patient-Specific EEG Management**: Upload and analyze EEG data for individual patients
- **Cognitive Assessment Tools**: Calculate engagement, focus, and relaxation scores
- **Multi-Patient Dashboard**: Manage multiple patients with individual profiles
- **Real Data Analysis**: Process authentic EEG datasets without synthetic data generation
- **Performance Monitoring**: View ML model accuracy and prediction capabilities
- **Export Functionality**: Generate detailed reports for clinical use

### General Users (Patients)
- **Music Therapy Portal**: Access to 5-genre melody database (Classical, Rock, Pop, Rap, R&B)
- **Interactive Music Player**: Full-featured audio player with controls
- **Neural Engagement Tracking**: Monitor personal brain response to music
- **Smart Recommendations**: AI-generated playlists based on engagement patterns
- **Personal Analytics**: View listening trends and neural engagement data
- **Progress Tracking**: Monitor therapeutic progress over time

## Security Notes

- Never commit `.env` or `.streamlit/secrets.toml` to version control
- Use Streamlit secrets for sensitive configuration (OAuth, Firestore)
- Implement proper session management in production
- Add HTTPS in production environments
- Validate and sanitize all user inputs

## Production Deployment

For production deployment:
1. Configure required Streamlit secrets (OAuth and Firestore)
2. Configure HTTPS
3. Use Firestore as the single source of truth (no local fallbacks)
4. Implement proper logging
5. Add error handling and monitoring
6. Set up backup and recovery procedures
