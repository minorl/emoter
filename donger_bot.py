import os
from pyparsing import alphanums, CaselessLiteral, Forward, Literal, NoMatch, StringEnd, Word
from slack.command import MessageCommand
from slack.parsing import symbols


class DongerBot:
    def __init__(self, max_len, binds_file='binds.csv'):
        self.max_len = max_len

        self.binds_file = binds_file 

        self.bind_name = 'Make Bind'
        self.bind_expr = (CaselessLiteral('bind') + Word(alphanums).setResultsName('key') + symbols.tail.setResultsName('output'))

        self.list_name = 'List Binds'
        self.list_expr = CaselessLiteral('list_binds')

        self.print_bind_name = 'Display Bind'
        # Use a forward to allow updating expression
        self.print_bind_forward = Forward().setResultsName('key')

        # Expression which is a MatchFirst of bound keys
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
        if len(output) > self.max_len:
            out_text = "Binds must be less than {} characters long".format(self.max_len)
            out_channel = None
        elif key in self.binds:
            out_text = "{} is already bound to {}.".format(key, self.binds[key])
            out_channel = None
        else:
            self.binds[key] = output
            with open(self.binds_file, 'a') as f:
                f.write('{},{}\n'.format(key, output))

            self.current_binds_expr |= Literal(key)
            self.print_bind_forward << self.current_binds_expr + StringEnd()

        if out_text:
            return MessageCommand(channel=out_channel, user=user, text=out_text)

    async def command_list(self, user, in_channel, parsed):
        res = ['{}: {}'.format(k, v) for k, v in self.binds.items()]
        return MessageCommand(channel=None, user=user, text='\n'.join(res))

    async def command_print_bind(self, user, in_channel, parsed):
        return MessageCommand(channel=in_channel, user=user, text=self.binds[parsed['key'][0]])

    def register_with_slack(self, slack):
        slack.register_handler(expr=self.bind_expr,
                               name=self.bind_name,
                               func=self.command_bind,
                               all_channels=True,
                               accept_dm=True,
                               doc="Bind a word to an output: bind <word> <output>.")

        slack.register_handler(expr=self.list_expr,
                               name=self.list_name,
                               func=self.command_list,
                               all_channels=True,
                               accept_dm=True,
                               doc="List the current binds: list_binds")

        # Must register this last so it won't overwrite other parts of grammar
        slack.register_handler(expr=self.print_bind_forward,
                               name=self.print_bind_name,
                               func=self.command_print_bind,
                               all_channels=True,
                               accept_dm=True)
