from googleapiclient.discovery import build
from oauth2client.client import SignedJwtAssertionCredentials
from herring.secrets import SECRETS, FUCK_OAUTH

service = build('drive', 'v2')

import httplib2
credentials = SignedJwtAssertionCredentials(
    FUCK_OAUTH['client_email'],
    FUCK_OAUTH['private_key'],
    'https://www.googleapis.com/auth/drive'
)
http = credentials.authorize(httplib2.Http())


def make_sheet(title):
    body = {
        'mimeType': 'application/vnd.google-apps.spreadsheet',
        'title': title,
        'parents': [{'id': SECRETS['gapps-folder']}]
    }
    got = service.files().insert(body=body).execute(http=http)

    # I don't know why it's called "alternateLink", but it's the link that
    # works.
    return got['alternateLink']
