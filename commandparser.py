from pyparsing import *


class CommandParser:
    def __init__(self, name):
        alert = CaselessLiteral(name).setResultsName('alert')
        emoji = Regex(':[\S]+:').setResultsName('emoji')
        message = OneOrMore(Word(alphanums + "#")).setResultsName('message')
        self.expr = alert + emoji + message

    def parse(self, s):
        return self.expr.parseString(s)
