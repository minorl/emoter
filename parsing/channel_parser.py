from pyparsing import *
from . import symbols
from .slack_parser import SlackParser


class ChannelParser(SlackParser):
    def __init__(self, name):
        self.expr = CaselessLiteral(name) + symbols.command
