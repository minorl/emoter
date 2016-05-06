import asyncio
import config
import emote_bot
import donger_bot
import react_bot
from mongoengine import connect
from slack.slack_api import Slack

connect('dongerbot')

slackapp = Slack(config.TOKEN, config.NAME)
e_bot = emote_bot.EmoteBot(channels=config.EMOJI_CHANNELS)
d_bot = donger_bot.DongerBot(admins=config.ADMINS, max_len=config.MAX_BIND_LEN)
r_bot = react_bot.ReactBot(slackapp, out_channels=config.REACTION_CHANNELS, max_per_user=config.MAX_REACTS_PER_CHANNEL)

e_bot.register_with_slack(slackapp)
r_bot.register_with_slack(slackapp)
# Need to register DongerBot second since it can add new grammar elements
d_bot.register_with_slack(slackapp)

loop = asyncio.get_event_loop()
loop.run_until_complete(slackapp.run())
