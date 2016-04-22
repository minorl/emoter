from pyparsing import *
from . import symbols
from .slack_parser import SlackParser


class PMParser(SlackParser):
    def __init__(self, name):
        self.expr = Optional(CaselessLiteral(name)) + Optional(symbols.channel_name) + symbols.command
