import random
import os
import praw

from elo_bot import SLACK_CLIENT


reddit = praw.Reddit(client_id=os.environ.get('REDDIT_CLIENT_ID'),
                     client_secret=os.environ.get('REDDIT_CLIENT_SECRET'),
                     user_agent='seal_bot')


SLACK_CLIENT.api_call(
    'chat.postMessage',
    channel='golden-seals',
    attachments=[
        {
            'image_url':random.choice(list(
                reddit.subreddit('seals').search('site=i.imgur.com'))).url,
            'title':'Go Seals!'
        }],
    as_user=True)
