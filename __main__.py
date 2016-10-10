import argparse
import asyncio
import binder_bot
import config
import emote_bot
import haiku_bot
from mongoengine import connect
import quote_bot
import react_bot
import sentiment_bot
import twitch_bot
import wordcloud_bot

from slack.slack_api import Slack
import tensorflow as tf

parser = argparse.ArgumentParser(description='A simple slack bot')
parser.add_argument('--load_history', action='store_true')
args = parser.parse_args()

connect(config.DB_NAME)

slackapp = Slack(config.TOKEN, config.ALERT, config.NAME, load_history=args.load_history)
e_bot = emote_bot.EmoteBot(channels=config.EMOJI_CHANNELS, slack=slackapp)
d_bot = binder_bot.BinderBot(admins=config.ADMINS, max_len=config.MAX_BIND_LEN, slack=slackapp)
r_bot = react_bot.ReactBot(admins=config.ADMINS, out_channels=config.REACTION_CHANNELS, max_per_user=config.MAX_REACTS_PER_CHANNEL, slack=slackapp)
q_bot = quote_bot.QuoteBot(slack=slackapp)
wc_bot = wordcloud_bot.WordcloudBot(slack=slackapp)

twitch_alias = 'twitch_db'
connect(config.TWITCH_DB_NAME, alias=twitch_alias)

t_bot = twitch_bot.TwitchBot(twitch_alias, min_length=config.MIN_MARKOV_LENGTH, slack=slackapp)

h_bot = haiku_bot.HaikuBot(slack=slackapp)

with tf.Graph().as_default(), tf.Session() as session:
    s_bot = sentiment_bot.SentimentBot(session=session, slack=slackapp)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(slackapp.run())
