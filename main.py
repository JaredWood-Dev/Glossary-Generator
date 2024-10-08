from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os.path

def auth():
    creds = None

    # Checks our "token", this basically stores if the user has already logged in to use the script
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json')
    # Otherwise, we need to log in
    if not creds or creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json')
            creds = flow.run_local_server(port=0)
        # Save the token
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds

def list_files():
    creds = auth()

    service = build('drive', 'v3', credentials=creds)

    # Call the API to get the items
    results = service.files().list(pageSize=100).execute()
    items = results.get('files', [])

    # If there is nothing, say so
    if not items:
        print("There are no files.")
    else:
        print("Files:")
        for file in items:
            print(f"{file['name']}")

list_files()