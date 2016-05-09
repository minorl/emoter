from pyparsing import CaselessLiteral, Group, NoMatch, Optional


class SlackParser():
    def __init__(self, alert='!'):
        self.dm_expr_head = Optional(CaselessLiteral(alert))
        self.expr_head = CaselessLiteral('!')
        self.command = NoMatch()
        self.reinit_exprs()

    def reinit_exprs(self):
        self.dm_expr = self.dm_expr_head + self.command
        self.expr = self.expr_head + self.command

    def parse(self, s, dm=False):
        return (self.dm_expr if dm else self.expr).parseString(s)

    def add_command(self, expr, name):
        self.command |= Group(expr).setResultsName(name)
        self.reinit_exprs()
