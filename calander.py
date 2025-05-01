import os
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from datetime import datetime, timedelta

# Load environment variables from .env file
load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/calendar']

def authenticate_google_calendar():
    # Construct the client configuration from environment variables
    client_config = {
        "installed": {
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "project_id": os.getenv("GOOGLE_PROJECT_ID"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            # Make sure the redirect URI here matches what's expected/configured in your Google Cloud Console creds
            "redirect_uris": [os.getenv("GOOGLE_REDIRECT_URI")] 
        }
    }

    # Validate that necessary variables were loaded
    if not all([client_config["installed"]["client_id"], client_config["installed"]["client_secret"], client_config["installed"]["project_id"], client_config["installed"]["redirect_uris"][0]]):
        print("Error: Missing one or more Google credentials in the .env file (GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_PROJECT_ID, GOOGLE_REDIRECT_URI).")
        return None
        
    try:
        # Use from_client_config instead of from_client_secrets_file
        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
        # Using port=0 lets the OS pick an available port automatically
        creds = flow.run_local_server(port=0)
        return creds
    except Exception as e:
        print(f"Authentication error: {str(e)}")
        # Specific error handling for port conflicts might still be relevant depending on the flow
        if "Only one usage of each socket" in str(e):
            print("\nPort conflict detected. Another application is using the specified port.")
        elif "invalid_grant" in str(e):
             print("\nError: Invalid grant. This might mean your credentials (client ID/secret) are wrong, or the refresh token is expired/revoked.")
        elif "redirect_uri_mismatch" in str(e):
             print(f"\nError: Redirect URI mismatch. Ensure the URI in your .env ('{os.getenv('GOOGLE_REDIRECT_URI')}') is registered in Google Cloud Console for your client ID.")
        return None

# Remove the duplicate authentication call
# creds = authenticate_google_calendar()

def get_tomorrow_events():
    creds = authenticate_google_calendar()
    if creds is None:
        # Enhanced error message propagation
        print("Failed to authenticate with Google Calendar. Cannot retrieve events.")
        return ["Authentication failed. Check previous error messages."]
        
    service = build('calendar', 'v3', credentials=creds)
    
    tomorrow = datetime.utcnow().date() + timedelta(days=1)
    start = datetime.combine(tomorrow, datetime.min.time()).isoformat() + 'Z'
    end = datetime.combine(tomorrow, datetime.max.time()).isoformat() + 'Z'

    try:
        events_result = service.events().list(
            calendarId='primary', timeMin=start, timeMax=end, singleEvents=True
        ).execute()

        events = events_result.get('items', [])
        if not events:
            return ["No events scheduled for tomorrow."]
            
        summaries = [f"{e['summary']} at {e.get('start', {}).get('dateTime', 'unknown time')}" for e in events]
        return summaries
    except Exception as e:
        # Log the full error for debugging, return a user-friendly message
        print(f"Error during API call: {str(e)}") 
        return [f"Error retrieving events. Check logs for details."]

# Usage:
if __name__ == "__main__":
    print("\nTomorrow's events:")
    events_list = get_tomorrow_events()
    for event in events_list:
        print(f"- {event}")
