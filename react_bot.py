from collections import defaultdict
from mongoengine import Document, StringField
from pyparsing import CaselessLiteral, nums, Optional, StringEnd, White, Word
from slack.command import EditReactionCommand, MessageCommand
import slack.parsing.symbols as sym
import re


class ReactDoc(Document):
    user = StringField()
    channel = StringField()
    regex = StringField()
    emoji = StringField()


class ReactBot:
    def __init__(self, slack, out_channels=set(), max_per_user=None):
        self.out_channels = out_channels
        self.max_per_user = max_per_user

        self.create_name = 'Add a reaction'
        self.create_expr = CaselessLiteral('react') + sym.channel_name + sym.emoji + White() + sym.tail

        self.clear_name = 'Remove a reaction'
        self.clear_expr = CaselessLiteral('unreact') + sym.channel_name + Word(nums).setResultsName('index') + StringEnd()

        self.list_name = 'List Reactions'
        self.list_expr = CaselessLiteral('list_react') + Optional(sym.channel_name) + StringEnd()
        self.load_reacts(slack)

    def load_reacts(self, slack):
        slack.preload_commands([EditReactionCommand(channel=r.channel, user=r.user, regex=re.compile(r.regex, re.IGNORECASE), emoji=r.emoji)
                               for r in ReactDoc.objects()])

    async def command_create(self, user, in_channel, parsed):
        target_channel = parsed['channel']
        reg_text = parsed['tail']
        emoji = parsed['emoji'][1:-1]

        react_objects = ReactDoc.objects(user=user, channel=target_channel)
        if target_channel not in self.out_channels:
            error_text = "Reactions in channel {} not permitted.".format(target_channel)
        elif len(react_objects) >= self.max_per_user:
            error_text = "Maximum number of emojis per channel reached."
        elif any(r.emoji == emoji and r.regex == reg_text for r in react_objects):
            error_text = "Reaction alreay registered."
        else:
            try:
                reg = re.compile(reg_text, re.IGNORECASE)
                react_obj = ReactDoc(user=user, channel=target_channel, regex=reg_text, emoji=emoji)
                react_obj.save()
                return EditReactionCommand(channel=target_channel,
                                           user=user,
                                           regex=reg,
                                           emoji=emoji)
            except re.error:
                error_text = "Invalid pattern."

        return MessageCommand(user=user, text=error_text)

    async def command_clear(self, user, in_channel, parsed):
        channel = parsed['channel']
        index = int(parsed['index'])
        react_objs = {(r.regex, r.emoji): r for r in ReactDoc.objects(user=user, channel=channel)}
        reacts = sorted(react_objs)
        if not 0 <= index < len(reacts):
            return MessageCommand(user=user, text="Invalid reaction number.")
        r_obj = react_objs[reacts[index]]
        command = EditReactionCommand(channel=channel, user=user, regex=re.compile(r_obj.regex, re.IGNORECASE), emoji=r_obj.emoji, remove=True)
        r_obj.delete()
        return command

    async def command_list(self, user, in_channel, parsed):
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
                res.append("\t{}. {} --> {}".format(i, reg, em))

        return MessageCommand(channel=None, user=user, text='\n'.join(res))

    def register_with_slack(self, slack):
        slack.register_handler(expr=self.create_expr,
                               name=self.create_name,
                               func=self.command_create,
                               all_channels=True,
                               accept_dm=True,
                               doc='Register a reaction for when a pattern occurs in a channel:\n'
                                   '\treact <channel> <emoji> <pattern>')

        slack.register_handler(expr=self.clear_expr,
                               name=self.clear_name,
                               func=self.command_clear,
                               all_channels=True,
                               accept_dm=True,
                               doc='Unregister a reaction. See list_react to get reaction nubmers:\n'
                                   '\tunreact <channel> <reaction number>')

        slack.register_handler(expr=self.list_expr,
                               name=self.list_name,
                               func=self.command_list,
                               all_channels=True,
                               accept_dm=True,
                               doc='List your registered reactions:\n'
                                   '\tlist_react [<channel>]')
