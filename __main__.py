import asyncio
import config
import emote_bot
import binder_bot
import react_bot
from mongoengine import connect
from slack.slack_api import Slack

connect(config.DB_NAME)

slackapp = Slack(config.TOKEN, config.ALERT)
e_bot = emote_bot.EmoteBot(channels=config.EMOJI_CHANNELS)
d_bot = binder_bot.BinderBot(admins=config.ADMINS, max_len=config.MAX_BIND_LEN)
r_bot = react_bot.ReactBot(slackapp, admins=config.ADMINS, out_channels=config.REACTION_CHANNELS, max_per_user=config.MAX_REACTS_PER_CHANNEL)

e_bot.register_with_slack(slackapp)
r_bot.register_with_slack(slackapp)
# Need to register BinderBot second since it can add new grammar elements
d_bot.register_with_slack(slackapp)

loop = asyncio.get_event_loop()
loop.run_until_complete(slackapp.run())
