from collections import defaultdict
from itertools import chain
import re

from mongoengine import Document, StringField
from pyparsing import CaselessLiteral, Literal, nums, Optional, printables, StringEnd, White, Word
from slack.bot import SlackBot, register
from slack.command import MessageCommand, ReactCommand
import slack.parsing.symbols as sym


class ReactDoc(Document):
    user = StringField()
    channel = StringField()
    regex = StringField()
    emoji = StringField()


class ReactBot(SlackBot):
    def __init__(self, *args, slack=None, admins=set(), out_channels=set(), max_per_user=None):
        self.admins = admins
        self.out_channels = out_channels
        self.max_per_user = max_per_user

        self.create_name = 'Add a reaction'
        self.create_expr = CaselessLiteral('react') + sym.channel_name + sym.emoji + White() + sym.tail
        self.create_doc = ('Register a reaction for when a pattern occurs in a channel:\n'
                           '\treact <channel> <emoji> <pattern>')

        self.clear_name = 'Remove a reaction'
        self.clear_expr = CaselessLiteral('unreact') + sym.channel_name + Word(nums).setResultsName('index') + StringEnd()
        self.clear_doc = ('Unregister a reaction. See list_react to get reaction nubmers:\n'
                          '\tunreact <channel> <reaction number>')

        self.list_name = 'List Reactions'
        self.list_expr = (CaselessLiteral('list_react') +
                          (Optional(Literal('--here').setResultsName('here')) &
                           Optional(Literal('--user') + Word(printables).setResultsName('user'))
                           ) +
                          Optional(sym.channel_name) + StringEnd())
        self.list_doc = ('List your registered reactions:\n'
                         '\tlist_react [<channel>]')

        self.reacts = defaultdict(lambda: defaultdict(set))
        for r in ReactDoc.objects():
            self.reacts[r.channel][r.user].add((re.compile(r.regex), r.emoji))

    @register(name='create_name', expr='create_expr', doc='create_doc')
    async def command_create(self, user, in_channel, parsed):
        target_channel = parsed['channel']
        reg_text = parsed['tail']
        emoji = parsed['emoji'][1:-1]

        if target_channel not in self.out_channels:
            text = "Reactions in channel {} not permitted.".format(target_channel)
        elif len(self.reacts[target_channel][user]) >= self.max_per_user:
            text = "Maximum number of emojis per channel reached."
        else:
            try:
                reg = re.compile(reg_text, re.IGNORECASE)
                react_obj = ReactDoc(user=user, channel=target_channel, regex=reg_text, emoji=emoji)
                react_obj.save()
                self.reacts[target_channel][user].add((reg, emoji))
                text = 'Reaction saved'
            except re.error:
                text = 'Invalid pattern.'

        return MessageCommand(user=user, channel=in_channel, text=text)

    @register(name='clear_name', expr='clear_expr', doc='clear_doc')
    async def command_clear(self, user, in_channel, parsed):
        channel = parsed['channel']
        index = int(parsed['index'])
        react_objs = {(r.regex, r.emoji): r for r in ReactDoc.objects(user=user, channel=channel)}
        reacts = sorted(react_objs)
        if not 0 <= index < len(reacts):
            text = 'Invalid reaction number.'
        else:
            r_obj = react_objs[reacts[index]]
            r_obj.delete()
            text = 'Reaction deleted.'

        return MessageCommand(user=user, channel=in_channel, text=text)

    @register(name='list_name', expr='list_expr', doc='list_doc')
    async def command_list(self, user, in_channel, parsed):
        to_user = user
        if 'user' in parsed and to_user in self.admins:
            user = parsed['user']
        elif 'user' in parsed:
            return MessageCommand(user=to_user, text="Not allowed.")
        else:
            user = to_user

        one_channel = 'channel' in parsed
        reacts = defaultdict(list)
        for react in (ReactDoc.objects(user=user, channel=parsed['channel'])
                      if one_channel else
                      ReactDoc.objects(user=user)):
            reacts[react.channel].append((react.regex, react.emoji))

        for l in reacts.values():
            l.sort()

        res = []
        for channel, l in reacts.items():
            res.append("Reactions in {}".format(channel))
            for i, (reg, em) in enumerate(l):
                res.append("\t{}. {} --> :{}:".format(i, reg, em))

        return MessageCommand(channel=in_channel if 'here' in parsed else None, user=to_user, text='\n'.join(res))

    @register(channels='out_channels')
    async def reaction_monitor(self, user, in_channel, message):
        result = []
        for reg, emoji in chain.from_iterable(self.reacts[in_channel].values()):
            if reg.search(message):
                result.append(ReactCommand(emoji))
        return result
