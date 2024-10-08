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

def list_files(id):
    creds = auth()

    service = build('drive', 'v3', credentials=creds)

    # Look inside a specific folder and
    query = f"'{id}' in parents and (mimeType = 'application/vnd.google-apps.document' or mimeType = 'application/vnd.google-apps.folder')"

    # Call the API to get the items
    results = service.files().list(q=query, fields="files(id, name, mimeType)").execute()
    items = results.get('files', [])

    # If there is nothing, say so
    if not items:

        # print("There are no files.")
        i = 0

    else:
        # print("Files:")
        for file in items:
            # If a file is actually a folder, search through that folder
            if file['mimeType'] == 'application/vnd.google-apps.folder':
                list_files(file['id'])
            if file['mimeType'] != 'application/vnd.google-apps.folder':
                print(f"{file['name']}")


def get_folder_id(folder_name):
    creds = auth()
    service = build('drive', 'v3', credentials=creds)

    query = f"name= '{folder_name}' and mimeType = 'application/vnd.google-apps.folder'"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    items = results.get('files', [])

    if not items:
        print(f"Unable to find {folder_name}.")
    else:
        folder = items[0]
        print(f"Found folder: {folder['name']}, id: {folder['id']}")
        return folder['id']


# Specify a folder by name
target_folder = 'Okarthel'

# Search for that folder and get the id
target_id = get_folder_id(target_folder)

# List the files in that target id
list_files(target_id)
