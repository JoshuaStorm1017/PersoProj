# drive_utils.py - Google Drive integration for Streamlit
import os
import pickle
import streamlit as st
import json
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# Files for storing auth data
TOKEN_FILE = 'token.pickle'
CLIENT_SECRET_FILE = 'client_secret.json'
SCOPES = ['https://www.googleapis.com/auth/drive']

def get_creds():
    """Get Google OAuth credentials - either from saved token or new auth flow"""
    creds = None
    
    # 1. Try to load existing token
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
    
    # 2. Check if credentials need refreshing or we need new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # We need to go through authentication flow
            return None
            
    # Save refreshed token if needed
    if os.path.exists(TOKEN_FILE) and creds and creds.valid:
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
            
    return creds

def setup_client_secret():
    """Create client_secret.json from Streamlit secrets or environment variables"""
    # Skip if file already exists
    if os.path.exists(CLIENT_SECRET_FILE):
        return True
        
    # Try to get credentials from Streamlit secrets
    if hasattr(st, 'secrets') and 'google_oauth' in st.secrets:
        client_id = st.secrets['google_oauth']['client_id']
        client_secret = st.secrets['google_oauth']['client_secret']
    else:
        # Fall back to environment variables
        client_id = os.environ.get('GOOGLE_CLIENT_ID')
        client_secret = os.environ.get('GOOGLE_CLIENT_SECRET')
        
    # Check if we have the credentials
    if not client_id or not client_secret:
        return False
        
    # Create the client_secret.json file
    client_config = {
        "web": {
            "client_id": client_id,
            "project_id": "my-perso-proj",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": client_secret,
            "redirect_uris": ["http://localhost:8501/"]
        }
    }
    
    with open(CLIENT_SECRET_FILE, 'w') as f:
        json.dump(client_config, f)
        
    return True

def authenticate():
    """Run the OAuth flow to get user permission"""
    if not os.path.exists(CLIENT_SECRET_FILE):
        st.error("Client secret file not found. Please set up your Google credentials.")
        return False
        
    # Create the flow using the client secrets file
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRET_FILE,
        scopes=SCOPES,
        redirect_uri="http://localhost:8501/"
    )
    
    # Generate the authorization URL
    auth_url, _ = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    
    # Show authentication instructions to user
    st.markdown("## Google Drive Authentication")
    st.markdown("1. Click this link to authorize your Google account:")
    st.markdown(f"2. [Authorize Google Drive Access]({auth_url})")
    st.markdown("3. After you approve, you'll be redirected to a page that might show an error. That's OK!")
    st.markdown("4. Copy the FULL URL from your browser address bar")
    
    # Get the redirect response from user
    redirect_response = st.text_input("Paste the full URL here:")
    
    if redirect_response:
        try:
            # Exchange auth code for access token
            flow.fetch_token(authorization_response=redirect_response)
            creds = flow.credentials
            
            # Save the credentials for future use
            with open(TOKEN_FILE, 'wb') as token:
                pickle.dump(creds, token)
                
            st.success("Authentication successful! You can now use Google Drive.")
            return True
        except Exception as e:
            st.error(f"Authentication error: {e}")
            return False
    
    return False

def get_drive_service():
    """Get an authorized Google Drive service"""
    creds = get_creds()
    if not creds:
        return None
        
    return build('drive', 'v3', credentials=creds)

def list_files(drive_service, query="", page_size=10):
    """List files from Google Drive"""
    try:
        results = drive_service.files().list(
            q=query,
            pageSize=page_size,
            fields="nextPageToken, files(id, name, mimeType, modifiedTime)"
        ).execute()
        return results.get('files', [])
    except Exception as e:
        st.error(f"Error listing files: {e}")
        return []

def save_to_drive(drive_service, data, file_name, folder_id=None):
    """Save data to Google Drive"""
    try:
        # Create temp file
        temp_file = f"temp_{file_name}"
        with open(temp_file, 'wb') as f:
            pickle.dump(data, f)
            
        # Set up file metadata
        file_metadata = {'name': file_name}
        if folder_id:
            file_metadata['parents'] = [folder_id]
            
        # Upload file to Drive
        media = MediaFileUpload(temp_file, resumable=True)
        file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        # Clean up temp file
        if os.path.exists(temp_file):
            os.remove(temp_file)
            
        return file.get('id')
    except Exception as e:
        st.error(f"Error saving to Drive: {e}")
        return None

def load_from_drive(drive_service, file_id):
    """Load data from a file in Google Drive"""
    try:
        # Create temp file for download
        temp_file = f"temp_download_{file_id}.pkl"
        
        # Download file
        request = drive_service.files().get_media(fileId=file_id)
        with open(temp_file, 'wb') as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
                
        # Load data from file
        with open(temp_file, 'rb') as f:
            data = pickle.load(f)
            
        # Clean up temp file
        if os.path.exists(temp_file):
            os.remove(temp_file)
            
        return data
    except Exception as e:
        st.error(f"Error loading from Drive: {e}")
        return None

def find_or_create_folder(drive_service, folder_name):
    """Find a folder by name or create it if it doesn't exist"""
    # Search for folder
    query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}'"
    results = list_files(drive_service, query)
    
    # Return existing folder if found
    if results:
        return results[0]['id']
        
    # Create new folder if not found
    try:
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        
        folder = drive_service.files().create(
            body=folder_metadata,
            fields='id'
        ).execute()
        
        return folder.get('id')
    except Exception as e:
        st.error(f"Error creating folder: {e}")
        return None