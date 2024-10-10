import requests.exceptions
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.api_core.exceptions import ResourceExhausted
import google.generativeai as genai
from googleapiclient.errors import HttpError
import time
import os
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


def list_files(id, file_type):
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
                file_list += list_files(file['id'], file['name'])
            if file['mimeType'] != 'application/vnd.google-apps.folder':
                if file_type != " ":
                    file['name'] += f" [{file_type}]"
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


def write_entry(id, text, header_no):
    creds = auth()
    docs_service = build('docs', 'v1', credentials=creds)

    if header_no == -1:
        requests = [
            {
                'insertText': {
                    'location': {
                        'index': 1,
                    },
                    'text': text + '\n'
                },
            },
            {
                'updateParagraphStyle': {
                    'range': {
                        'startIndex': 1,
                        'endIndex': len(text)
                    },
                    'paragraphStyle': {
                        'namedStyleType': 'NORMAL_TEXT'
                    },
                    'fields': 'namedStyleType'
                }
            }
        ]
    else:
        requests = [
            {
                'insertText': {
                    'location': {
                        'index': 1,
                    },
                    'text': text + '\n'
                },
            },
            {
                'updateParagraphStyle': {
                    'range': {
                        'startIndex': 1,
                        'endIndex': len(text)
                    },
                    'paragraphStyle': {
                        'namedStyleType': f'HEADING_{header_no}'
                    },
                    'fields': 'namedStyleType'
                }
            }
        ]


    result = docs_service.documents().batchUpdate(
        documentId=id,
        body={'requests': requests}
    ).execute()

    print("File written!")

    return True


def generate_desc(file):
    creds = auth()
    docs_service = build('docs', 'v1', credentials=creds)

    document = docs_service.documents().get(documentId=file).execute()

    doc_content = document.get('body').get('content')

    # This is the text of the given file, next we want to give this to an ai to write a description of it.
    doc_text = ''.join([element['paragraph']['elements'][0]['textRun']['content']
                        for element in doc_content
                        if 'paragraph' in element and 'elements' in element['paragraph']
                        and 'textRun' in element['paragraph']['elements'][0]])

    # print(doc_text)
    # AI Model
    model = genai.GenerativeModel("gemini-1.5-flash")

    prompt = "I need you so summarize the following text, but with the following notes; output only the summary, try to keep the summary at most 5 sentences, but it can be less. if the summary is of a geographic location(like a town, government, or thing) list its location, if the summary is of a magic item list its rarity and what type it is. This generation is within the context of a Dungeons and Dragons 5e    game." + doc_text

    # Response
    response = model.generate_content(prompt)

    return "\t" + response.text


# This function will try the provided function, and exponentially back-off if needed
def try_back_off(function, *args, retries=10, initial_delay=1, backoff_factor=2):
    delay = initial_delay
    for attempt in range(retries):
        try:
            return function(*args)
        except ResourceExhausted as e:
            print(f"Quota Exceeded: '{e}' Trying Again in '{delay}'...")
            time.sleep(delay)
            delay *= backoff_factor
        except HttpError as e:
            if e.resp.status in [500, 503]:
                print(f"Server Error: '{e}' Trying Again in '{delay}'...")
                time.sleep(delay)
                delay *= backoff_factor
            else:
                raise
        except ValueError as e:
            print(f"Value Error: '{e}'\n The AI thinks the prompt is harmful!")
        except requests.exceptions.Timeout as e:
            print(f"Error: '{e}', Trying Again...")
    raise Exception("Service still unavailable!")


# Get the starting time
start_time = time.time()

# Specify a folder by name
target_folder = 'Okarthel'

# Search for that folder and get the id
target_id = get_folder_id(target_folder)

# List the files in that target id
master_list = list_files(target_id, " ")


# Time after getting all files
list_time = time.time()

# Sort the list
master_list.sort(key=lambda x: x['name'], reverse=True)

total_files = 0
# Print the master list
for file in master_list:
    print(f"{file['name']}")
    total_files += 1

# Create the output Google Document
glossary = create_doc()

# Next, write to the document
for file in master_list:
    print(f"Generating description for {file['name']}")
    desc = try_back_off(generate_desc, file['id'])

    try_back_off(write_entry, glossary, desc, -1)

    try_back_off(write_entry, glossary, file['name'], 2)

write_entry(glossary, "Okarthel Lore Glossary", 1)

# Time at the end
final_time = time.time()

list_time = round(list_time - start_time, 2)
final_time = round(final_time - start_time, 2)

print(f"Time after getting all files: {list_time} seconds.")
print(f"Time after completion: {final_time} seconds.")
print(f"Total files processed: {total_files}.")
