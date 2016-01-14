from celery import shared_task
from puzzles.models import Puzzle
from puzzles.spreadsheets import make_sheet
import slacker
try:
    from herring.secrets import SECRETS
    # A token logged in as a legitimate user. Turns out that "bots" can't
    # do the things we want to automate!
    SLACK = slacker.Slacker(SECRETS['slack-user-token'])
except ImportError:
    print(
        "Couldn't find herring/herring/secrets.py. This server won't be able "
        "to use Slack and Google Drive integrations."
    )
    SLACK = None


@shared_task
def create_puzzle_sheet_and_channel(slug):
    puzzle = Puzzle.objects.get(slug=slug)
    sheet_title = '{} {}'.format(puzzle.identifier(), puzzle.name)
    sheet_url = make_sheet(sheet_title).rsplit('?', 1)[0]

    puzzle.url = sheet_url
    puzzle.save()

    channel_name = '#' + slug
    try:
        created = SLACK.channels.create(channel_name)
    except slacker.Error:
        created = SLACK.channels.join(channel_name)

    channel_id = created.body['channel']['id']
    topic = "{name} - {url} - Spreadsheet: {sheet}".format(
        name=puzzle.name,
        url=puzzle.hunt_url,
        sheet=sheet_url
    )
    SLACK.channels.set_topic(channel_id, topic)
    
    response = SLACK.channels.join('puzzle-status')
    status_channel_id = response.body['channel']['id']

    new_channel_msg = "New puzzle created: #{slug} {name}".format(
        slug=slug, name=puzzle.name
    )

    SLACK.chat.post_message(status_channel_id, new_channel_msg, link_names=True)
