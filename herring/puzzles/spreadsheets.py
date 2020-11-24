import logging
from datetime import datetime
from django.conf import settings
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from lazy_object_proxy import Proxy as lazy_object


@lazy_object
def service():
    if not settings.HERRING_ACTIVATE_GAPPS:
        logging.warning("Running without GApps integration!")
        return None
    try:
        logging.info("settings: %s", settings.HERRING_FUCK_OAUTH)
        credentials = Credentials.from_service_account_info(
            settings.HERRING_FUCK_OAUTH,
            scopes=['https://www.googleapis.com/auth/drive'])
        return build('drive', 'v3', credentials=credentials, cache_discovery=False)
    except ValueError as e:
        logging.error("Couldn't get the google drive service", exc_info=True)
        return None


def make_sheet(title):
    body = {
        'mimeType': 'application/vnd.google-apps.spreadsheet',
        'name': title,
        'parents': [settings.HERRING_SECRETS['gapps-folder']]
    }
    got = service.files().create(body=body).execute()
    return got['id']


def iterate_changes(page_token=None):
    if page_token is None:
        page_token = service.changes().getStartPageToken().execute()['startPageToken']

    while page_token is not None:
        req = service.changes().list(
            fields='nextPageToken,newStartPageToken,changes(fileId,time)',
            pageToken=page_token,
            spaces='drive')
        result = req.execute()
        changes = result.get('changes')
        if changes is not None:
            for change_data in changes:
                change = SheetChange(change_data)
                if change.sheet_id is not None:
                    yield change

        page_token = result.get('nextPageToken')

    return result['newStartPageToken']


class SheetChange:
    def __init__(self, change):
        self._change = change
        self.sheet_id = change.get('fileId')

    @property
    def datetime(self):
        return datetime.fromisoformat(
            self._change['time'].replace('Z', '+00:00'))
