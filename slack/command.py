import abc


class Command(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    async def execute(self, slack):
        pass


class MessageCommand(Command):
    def __init__(self, channel=None, user=None, text=''):
        self.channel = channel
        self.user = user
        self.text = text

    async def execute(self, slack):
        channel = slack.c_name_to_id[self.channel] if self.channel else slack.u_name_to_dm[self.user]
        if len(self.text) < 4000:
            await slack.send(self.text, channel)


class EditReactionCommand(Command):
    def __init__(self, channel=None, user=None, regex=None, emoji=None, remove=False):
        self.channel = channel
        self.user = user
        self.regex = regex
        self.emoji = emoji
        self.remove = remove

    async def execute(self, slack):
        c_id = slack.c_name_to_id[self.channel]
        if self.remove:
            slack.reactions[c_id][self.user].discard((self.regex, self.emoji))
        else:
            slack.reactions[c_id][self.user].add((self.regex, self.emoji))
