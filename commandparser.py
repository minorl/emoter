from pyparsing import *


class CommandParser:
    def __init__(self):
        alert = CaselessLiteral('dankbot').setResultsName('alert')
        emoji = Word(printables).setResultsName('emoji')
        message = OneOrMore(Word(alphanums + "#")).setResultsName('message')
        self.expr = alert + emoji + message

    def parse(self, s):
        return self.expr.parseString(s)
