from functools import reduce
from pyparsing import CaselessLiteral, Group, NoMatch, Optional


class SlackParser():
    def __init__(self, alert='!'):
        self.dm_expr_head = Optional(CaselessLiteral(alert))
        self.expr_head = CaselessLiteral('!')
        self.commands = []
        self.reinit_exprs()

    def reinit_exprs(self):
        command = reduce(lambda acc, e: acc | e[1], self.commands, NoMatch())
        self.dm_expr = self.dm_expr_head + command
        self.expr = self.expr_head + command

    def parse(self, s, dm=False):
        return (self.dm_expr if dm else self.expr).parseString(s)

    def add_command(self, expr, name, priority=0):
        # TODO: Make this not bad
        add_expr = Group(expr).setResultsName(name)
        for i, (p, e) in enumerate(self.commands):
            if priority >= p:
                self.commands.insert(i, (priority, add_expr))
                break
        else:
            self.commands.append((priority, add_expr))
        self.reinit_exprs()
