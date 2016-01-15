from googleapiclient.discovery import build
from oauth2client.client import SignedJwtAssertionCredentials
import httplib2
import requests

service = build('drive', 'v2')

try:
    from herring.secrets import SECRETS, FUCK_OAUTH

    credentials = SignedJwtAssertionCredentials(
        FUCK_OAUTH['client_email'],
        FUCK_OAUTH['private_key'],
        'https://www.googleapis.com/auth/drive'
    )
    http = credentials.authorize(httplib2.Http())
    shortener_url = 'https://www.googleapis.com/urlshortener/v1/url?key={}'.format(SECRETS['google-api-key'])
except KeyError:
    http = None
    shortener_url = 'https://www.googleapis.com/urlshortener/v1/url'


def shorten_url(url):
    response = requests.post(shortener_url, json={'longUrl': url})
    short_url = response.json()['id']
    return short_url


def make_sheet(title):
    body = {
        'mimeType': 'application/vnd.google-apps.spreadsheet',
        'title': title,
        'parents': [{'id': SECRETS['gapps-folder']}]
    }
    got = service.files().insert(body=body).execute(http=http)

    # I don't know why it's called "alternateLink", but it's the link that
    # works.
    long_url = got['alternateLink']
    return shorten_url(long_url)
