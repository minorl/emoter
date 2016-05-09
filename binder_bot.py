from collections import namedtuple
from functools import reduce
from mongoengine import Document, StringField
from pyparsing import alphanums, CaselessLiteral, Forward, Literal, NoMatch, StringEnd, Word
from slack.bot import SlackBot, register
from slack.command import MessageCommand
from slack.parsing import symbols


Bind = namedtuple('Bind', ['user', 'output'])


class BindDoc(Document):
    key = StringField()
    user = StringField()
    output = StringField()


class BinderBot(SlackBot):
    def __init__(self, max_len, admins=set(), slack=None):
        self.max_len = max_len
        self.admins = admins

        key_expr = Word(alphanums + '{}').setResultsName('key')

        self.bind_name = 'Make Bind'
        self.bind_expr = CaselessLiteral('bind') + key_expr + symbols.tail.setResultsName('output') + StringEnd()
        self.bind_doc = 'Bind a word to an output: bind <word> <output>.'

        self.unbind_name = 'Remove Bind'
        self.unbind_expr = CaselessLiteral('unbind') + key_expr + StringEnd()
        self.unbind_doc = 'Unbind a bound word: unbind <word>'

        self.list_name = 'List Binds'
        self.list_expr = CaselessLiteral('list_binds') + StringEnd()
        self.list_doc = 'List the current binds: list_binds'

        self.print_bind_name = 'Display Bind'
        # Use a forward to allow updating expression
        # Expression which is a MatchFirst of bound keys
        self.print_bind_forward = Forward().setResultsName('key')

        self.load_binds()

    def load_binds(self):
        self.binds = {}
        self.current_bind_exprs = {}
        for bind in BindDoc.objects:
            self.binds[bind.key] = Bind(bind.user, bind.output)
            self.current_bind_exprs[bind.key] = (Literal(bind.key))

        self.update_bind_expr()

    def update_bind_expr(self):
        self.print_bind_forward << reduce(lambda acc, i: acc | i, self.current_bind_exprs.values(), NoMatch()) + StringEnd()

    @register(name='bind_name', expr='bind_expr', doc='bind_doc')
    async def command_bind(self, user, in_channel, parsed):
        output = parsed['output']
        key = parsed['key']
        out_text = ''
        if len(output) > self.max_len:
            out_text = 'Binds must be less than {} characters long'.format(self.max_len)
            out_channel = None
        elif key in self.binds:
            out_text = '{} is already bound to {}.'.format(key, self.binds[key].output)
            out_channel = None
        else:
            self.binds[key] = Bind(user, output)

            # Write bind to mongo
            bind = BindDoc(key=key, user=user, output=output)
            bind.save()

            self.current_bind_exprs[key] = (Literal(key))
            self.update_bind_expr()

        if out_text:
            return MessageCommand(channel=out_channel, user=user, text=out_text)

    @register(name='unbind_name', expr='unbind_expr', doc='unbind_doc')
    async def command_unbind(self, user, in_channel, parsed):
        key = parsed['key']
        out_text = None
        if key not in self.binds:
            out_text = '{} is not bound.'.format(key)
            out_channel = None
        elif user not in self.admins and self.binds[key].user != user:
            out_text = 'You may only unbind your own binds.'
            out_channel = None
        else:
            bind_obj = BindDoc.objects(key=key)
            bind_obj.delete()
            del self.current_bind_exprs[key]
            del self.binds[key]
            self.update_bind_expr()

        if out_text:
            return MessageCommand(channel=out_channel, user=user, text=out_text)

    @register(name='list_name', expr='list_expr', doc='list_doc')
    async def command_list(self, user, in_channel, parsed):
        res = ['{}: {}'.format(k, v.output) for k, v in self.binds.items()]
        return MessageCommand(channel=None, user=user, text='\n'.join(res))

    @register(name='print_bind_name', expr='print_bind_forward', priority=-1)
    async def command_print_bind(self, user, in_channel, parsed):
        return MessageCommand(channel=in_channel, user=user, text=self.binds[parsed['key'][0]].output)
