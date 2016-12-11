from slack.bot import SlackBot, register
from slack.command import MessageCommand, ReactCommand



class JeffBot(SlackBot):
    def __init__(self, slack=None):
        self.channels = {"dankmemeseses"}

    @register(channels='channels')
    async def command_jeff(self, user, in_channel, message):
    	if user == "skelni":
    		return ReactCommand("shit")
    	else:
    		return None
