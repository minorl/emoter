import os
from pyparsing import alphanums, CaselessLiteral, Forward, Literal, NoMatch, StringEnd, Word
from slack.command import MessageCommand
from slack.parsing import symbols


class DongerBot:
    def __init__(self):
        self.binds_file = 'binds.csv'

        self.bind_name = 'command_bind'
        self.bind_expr = (CaselessLiteral('bind') + Word(alphanums).setResultsName('key') + symbols.tail.setResultsName('output'))
        # Expression which is a MatchFirst of bound keys

        self.print_bind_name = 'command_print_bind'
        # Use a forward to allow updating expression
        self.print_bind_forward = Forward().setResultsName('key')
        self.current_binds_expr = NoMatch()
        self.load_binds()

    def load_binds(self):
        self.binds = {}
        if os.path.exists(self.binds_file):
            with open(self.binds_file) as f:
                self.binds = {c: d.strip() for c, d in (line.split(',', 1) for line in f)}
        else:
                self.binds = {}
        for k in self.binds:
            self.current_binds_expr |= Literal(k)

        self.print_bind_forward << self.current_binds_expr + StringEnd()

    async def command_bind(self, user, in_channel, parsed):
        output = parsed['output']
        key = parsed['key']
        out_text = ''
        if len(output) > 40:
            out_text = "Binds must be less than 40 characters long"
            out_channel = None
        elif key in self.binds:
            out_text = "{} is already bound to {}.".format(key, self.binds[key])
            out_channel = None
        else:
            self.binds[key] = output
            with open(self.binds_file, 'a') as f:
                f.write('{},{}\n'.format(key, output))

            self.current_binds_expr |= Literal(key)
            self.print_bind_forward << self.current_binds_expr

        if out_text:
            return MessageCommand(channel=out_channel, user=user, text=out_text)

    async def command_print_bind(self, user, in_channel, parsed):
        return MessageCommand(channel=in_channel, user=user, text=self.binds[parsed['key']])

    def register_with_slack(self, slack):
        slack.register_handler(expr=self.bind_expr,
                               name=self.bind_name,
                               func=self.command_bind,
                               all_channels=True,
                               accept_dm=True,
                               doc="Bind a word to an output: bind <word> <output>.")

        slack.register_handler(expr=self.print_bind_forward,
                               name=self.print_bind_name,
                               func=self.command_print_bind,
                               all_channels=True,
                               accept_dm=True)
