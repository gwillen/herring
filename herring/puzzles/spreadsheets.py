from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from herring.secrets import SECRETS, FUCK_OAUTH

try:
    credentials = Credentials.from_service_account_info(
        FUCK_OAUTH,
        scopes=['https://www.googleapis.com/auth/drive'])
    service = build('drive', 'v2', credentials=credentials)
except ValueError:
    pass


def make_sheet(title):
    body = {
        'mimeType': 'application/vnd.google-apps.spreadsheet',
        'title': title,
        'parents': [{'id': SECRETS['gapps-folder']}]
    }
    got = service.files().insert(body=body).execute()

    # I don't know why it's called "alternateLink", but it's the link that
    # works.
    return got['alternateLink']
