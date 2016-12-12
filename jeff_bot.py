from pyparsing import CaselessLiteral, StringEnd
from slack.bot import SlackBot, register
from slack.command import MessageCommand, ReactCommand
from slack.parsing import symbols


class JeffBot(SlackBot):
    def __init__(self, jeff_channels, slack=None):
        self.channels = jeff_channels
        self.pig_name = "Pig Latin"
        self.pig_expr = CaselessLiteral("pig") + symbols.tail.setResultsName("message") + StringEnd()
        self.pig_doc = "Translate a message to pig latin"

    @register(channels='channels')
    async def command_jeff(self, user, in_channel, message):
        if user == "skelni":
            return ReactCommand("shit")
        else:
            return None

    @register(name="pig_name", expr="pig_expr", doc="pig_doc")
    async def command_pig_latin(self, user, in_channel, parsed):
        message = parsed["message"]
        return MessageCommand(text=pig_latin(message), channel=in_channel, user=user)

def pig_latin(words):
    vowels = {"a", "e", "i", "o", "u"}
    new = []
    for word in words.lower().split():
        if word[0] in vowels:
            new.append(word + "way")
        else:
            start = 0
            for letter in list(word):
                if letter in vowels:
                    break
                else:
                    start += 1
            new.append(word[start:] + word[:start] + "ay")
    return " ".join(new)
