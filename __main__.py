import asyncio
import config
import emote_bot
import donger_bot
from slack.slack_api import Slack

slackapp = Slack(config.TOKEN, config.NAME)
e_bot = emote_bot.EmoteBot(config.CHANNELS)
d_bot = donger_bot.DongerBot()

e_bot.register_with_slack(slackapp)
d_bot.register_with_slack(slackapp)

loop = asyncio.get_event_loop()
loop.run_until_complete(slackapp.run())
