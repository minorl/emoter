import asyncio
import config
import emotebot
from slack.slack_api import Slack

slackapp = Slack(config.TOKEN)
bot = emotebot.EmoteBot(config.CHANNELS, config.NAME)

slackapp.register_handler(bot.channel_command, channels=config.CHANNELS)
slackapp.register_handler(bot.pm_command)

loop = asyncio.get_event_loop()
loop.run_until_complete(slackapp.run())
