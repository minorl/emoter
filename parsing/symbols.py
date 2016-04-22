from pyparsing import *


emoji = Regex(':[\S]+:').setResultsName('emoji')

message = OneOrMore(Word(alphanums + "#")).setResultsName('message')

channel_name = Word(alphanums).setResultsName('channel')

emoji_command = (emoji + message).setResultsName('command_emoji')
command = emoji_command
