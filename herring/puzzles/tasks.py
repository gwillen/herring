from celery import shared_task
from puzzles.models import Puzzle
from puzzles.spreadsheets import make_sheet
from herring.secrets import SECRETS
import slacker

# A token logged in as a legitimate user. Turns out that "bots" can't
# do the things we want to automate!
SLACK = slacker.Slacker(SECRETS['slack-user-token'])


@shared_task
def create_puzzle_sheet_and_channel(slug):
    puzzle = Puzzle.objects.get(slug=slug)
    sheet_title = '{} {}'.format(puzzle.identifier(), puzzle.name)
    sheet_url = make_sheet(sheet_title)

    puzzle.url = sheet_url
    puzzle.save()

    channel_name = '#' + slug
    try:
        created = SLACK.channels.create(channel_name)
    except slacker.Error:
        created = SLACK.channels.join(channel_name)

    channel_id = created.body['channel']['id']
    SLACK.channels.set_topic(channel_id, puzzle.name)
    SLACK.channels.set_purpose(channel_id, 'solving "{}", at {}'.format(puzzle.name, puzzle.hunt_url))
    
    sheet_link = 'Spreadsheet: {}'.format(sheet_url)
    posted = SLACK.chat.post_message(channel_id, sheet_link)
    msg_timestamp = posted.body['ts']
    SLACK.pins.add(channel_id, timestamp=msg_timestamp)

