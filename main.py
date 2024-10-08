from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import os.path


def auth():
    creds = None

    SCOPES = [
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/documents"
    ]

    # Checks our "token", this basically stores if the user has already logged in to use the script
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # Otherwise, we need to log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
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

    # Create a list of all files
    file_list = []

    # If there is nothing, say so
    if not items:

        # print("There are no files.")
        i = 0

    else:
        # print("Files:")
        for file in items:
            # If a file is actually a folder, search through that folder
            if file['mimeType'] == 'application/vnd.google-apps.folder':
                file_list += list_files(file['id'])
            if file['mimeType'] != 'application/vnd.google-apps.folder':
                file_list.append(file)
                print(f"Added {file['name']} to list!")

    return file_list


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



def create_doc():
    creds = auth()
    service = build('drive', 'v3', credentials=creds)

    # Make a new doc
    file_metadata = {
        'name': 'Lore Glossary',
        'mimeType': 'application/vnd.google-apps.document'
    }

    file = service.files().create(body=file_metadata, fields='id').execute()

    print(f"Created file with ID: {file.get('id')}")

    return file.get('id')


def write_entry(id):
    creds = auth()
    docs_service = build('docs', 'v1', credentials=creds)

    requests = [
        {
            'insertText': {
                'location': {
                    'index': 1,
                },
                'text': 'Hello World!'
            }
        }
    ]

    result = docs_service.documents().batchUpdate(
        documentId=id,
        body={'requests': requests}
    ).execute()

    print("File written!")


# Specify a folder by name
target_folder = 'Youtube'

# Search for that folder and get the id
target_id = get_folder_id(target_folder)

# List the files in that target id
master_list = list_files(target_id)

# Sort the list
master_list.sort(key=lambda x: x['name'])

# Print the master list
for file in master_list:
    print(f"{file['name']}")

# Create the output Google Document
glossary = create_doc()

# Next, write to the document
write_entry(glossary)
