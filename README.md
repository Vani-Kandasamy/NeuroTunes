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
- **Interactive Music Player**: Play/pause controls and simple playback UI
- **Trend Analysis**: Category listening summary plus "Top Track This Session"
- **Caregiver-Linked Recs**: If a caregiver saved recommendations for your email, they surface on your dashboard
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
- **ML Model Performance Dashboard**: View model accuracy, capabilities, and performance metrics
- **Cognitive Insights Visualization**: Interactive charts showing brain response patterns per patient
- **Real EEG Data Upload**: CSV import functionality for authentic EEG datasets (no synthetic data)

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Go to Google Cloud Console → Create/select a project.
3. Set up OAuth Consent Screen → Configure app details & scopes.
4. In Navigation menu -> APIs & Services -> OAuth Consent Screen
5. Create OAuth Credentials → Select “Web Application” and set redirect URIs.
6. In Navigation menu -> APIs & Services -> Credentials
7. In Create Credentials -> Create OAuth Client Under "Application type", select "Web application".
8. Under "Authorized redirect URIs", add the Path where Google will redirect users after they have authenticated
   Redirect URI for this app: https://braintunes.streamlit.app/oauth2callback


### 3. Creating a Firestore database in the Google Cloud Console


1. In the left-hand navigation menu, click on "APIs & Services" > "Library".
2. In the search bar, type "Firestore" and select "Cloud Firestore API" from the results.
3. Click the "Enable" button to enable the Firestore API for your project.
4. In the left-hand navigation menu, scroll down and click on "Firestore".
5. Choose a Database Location closest to you
6. Database id should be (default) - Don’t change it
7. Choose Database Mode as Native
8. Create the database
9. Set up initial security rules to control access to your database.

### 4. Creating Service account for the project
1. Creating a service account in Google Cloud Console is crucial for managing permissions and enabling secure, programmatic access to your projects
2. Select the project for which you want to create a service account.
3. In the left-hand sidebar, click on "IAM & Admin" and then select "Service Accounts"
4. Click on the "Create Service Account" button at the top of the Service Accounts page
5. Enter a name for your service account and Service Account ID will be automatically created
6. On the Permissions page, add a role to the service account (Owner)
7. Generate Service Account Key: Navigate to the "Keys" section and click "Add Key" > "Create New Key".

```toml
[auth]
redirect_uri = "https://braintunes.streamlit.app/oauth2callback"  
cookie_secret = "123"
client_id = "copy from google cloud console"  
client_secret = "copy from google cloud console"  
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"

[gcp_service_account]
type = "service_account"
project_id = "copy from json downloaded after creating service account"
private_key_id = ""
private_key = ""
client_email = ""
client_id = ""
auth_uri = ""
token_uri = ""
auth_provider_x509_cert_url = ""
client_x509_cert_url = ""
```


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

### Notes

- Default songs are automatically seeded into Firestore on first load if the `songs` collection is empty (no manual admin action required).

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
- **Personal Analytics**: View listening trends and neural engagement data

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
