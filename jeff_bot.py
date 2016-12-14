from pyparsing import CaselessLiteral, StringEnd
from random import randint, choice
from slack.bot import SlackBot, register
from slack.command import MessageCommand, ReactCommand
from slack.parsing import symbols


class JeffBot(SlackBot):
    def __init__(self, emoji_random, jeff_channels, jeff_bot_target, slack=None):
        self.channels = jeff_channels
        self.pig_name = "Pig Latin"
        self.pig_expr = CaselessLiteral("pig") + symbols.tail.setResultsName("message") + StringEnd()
        self.pig_doc = "Translate a message to pig latin"
        self.hankey_name = "Hankey"
        self.hankey_expr = CaselessLiteral("hankey") + symbols.user_name.setResultsName("target") + StringEnd()
        self.hankey_doc = "Target user for hankeying"
        self.target = jeff_bot_target
        self.random = emoji_random

    @register(channels="channels")
    async def command_random(self, user, in_channel, message):
        if user == "skelni" and randint(0,19) == 1:
            return ReactCommand(choice(self.random))
        else:
            return None

    @register(channels="channels")
    async def command_jeff(self, user, in_channel, message):
        if user == self.target:
            return ReactCommand("hankey")
        else:
            return None

    @register(name="hankey_name", expr="hankey_expr", doc="hankey_doc")
    async def command_hankey(self, user, in_channel, parsed):
        self.target = parsed["target"]
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
