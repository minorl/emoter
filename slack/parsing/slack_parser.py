from pyparsing import *
from . import symbols

class SlackParser():
    def __init__(self, name):
        self.dm_expr_head = Optional(CaselessLiteral(name))
        self.expr_head = CaselessLiteral(name)
        self.command = NoMatch()
        self.reinit_exprs()

    def reinit_exprs(self):
        self.dm_expr =  self.dm_expr_head + self.command
        self.expr = self.expr_head + self.command

    def parse(self, s, dm=False):
        return (self.dm_expr if dm else self.expr).parseString(s)

    def add_command(self, expr):
        self.command |= expr
        self.reinit_exprs()
