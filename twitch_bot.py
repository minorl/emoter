from pyparsing import alphanums, CaselessLiteral, Optional, StringEnd, Word
from slack.bot import SlackBot, register
from slack.command import MessageCommand
from twitchlogger.markov import MarkovTwitchEmulator


class TwitchBot(SlackBot):
    def __init__(self, twitch_db_alias, min_length=1, slack=None):
        self.markov = MarkovTwitchEmulator(twitch_db_alias, min_length=min_length)

        self.twitch_name = 'Twitch Chat'
        self.twitch_expr = (CaselessLiteral('twitch') + Optional(Word(alphanums + '_-').setResultsName('twitch_channel'))) + StringEnd()
        self.twitch_doc = "Markov emulate a twitch channel: twitch [channel]"

    @register(name='twitch_name', expr='twitch_expr', doc='twitch_doc')
    async def command_twitch(self, user, in_channel, parsed):
        # None if not found
        twitch_channel = parsed.get('twitch_channel')
        if twitch_channel and not twitch_channel.startswith('#'):
            twitch_channel = '#' + twitch_channel

        if twitch_channel not in self.markov.probabilities:
            out_text = "Channel {} not recognized. If you would like this channel added, ask a bot admin.".format(twitch_channel)
            out_channel = None
        else:
            out_channel = in_channel
            out_text = self.markov.generate_message(twitch_channel)

        if out_channel is None:
            return MessageCommand(text=out_text, user=user)
        else:
            return MessageCommand(text=out_text, channel=out_channel)
