import asyncio
import config
import emote_bot
import binder_bot
import react_bot
from mongoengine import connect
import wordcloud_bot
from slack.slack_api import Slack

connect(config.DB_NAME)

slackapp = Slack(config.TOKEN, config.ALERT, config.NAME)
e_bot = emote_bot.EmoteBot(channels=config.EMOJI_CHANNELS, slack=slackapp)
d_bot = binder_bot.BinderBot(admins=config.ADMINS, max_len=config.MAX_BIND_LEN, slack=slackapp)
r_bot = react_bot.ReactBot(admins=config.ADMINS, out_channels=config.REACTION_CHANNELS, max_per_user=config.MAX_REACTS_PER_CHANNEL, slack=slackapp)
wc_bot = wordcloud_bot.WordcloudBot(slack=slackapp)


loop = asyncio.get_event_loop()
loop.run_until_complete(slackapp.run())
