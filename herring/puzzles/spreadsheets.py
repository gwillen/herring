from googleapiclient.discovery import build
from oauth2client import crypt
from oauth2client.service_account import ServiceAccountCredentials
import httplib2

try:
    from herring.secrets import SECRETS, FUCK_OAUTH

    credentials = ServiceAccountCredentials(
        service_account_email=FUCK_OAUTH['client_email'],
        signer=crypt.OpenSSLSigner.from_string(FUCK_OAUTH['private_key']),
        scopes='https://www.googleapis.com/auth/drive'
    )
    service = build('drive', 'v2', credentials=credentials)

    http = credentials.authorize(httplib2.Http())
except KeyError:
    http = None


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
