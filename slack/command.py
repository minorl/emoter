import abc
from collections import namedtuple
from .history import HistoryDoc
import os


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
            slack.reactions[c_id][self.user].remove((self.regex, self.emoji))
        else:
            slack.reactions[c_id][self.user].add((self.regex, self.emoji))


Record = namedtuple('Record', ['channel', 'user', 'text', 'times'])


class HistoryCommand(Command):
    """
    Pass a callback to slack with signature: f(hist_list) where hist is a list of (channel, user, text, time) namedtuples.
    For direct messages, channel will be #dm.
    """
    def __init__(self, callback, channel=None, user=None):
        self.callback = callback
        self.channel = channel
        self.user = user

    async def execute(self, slack):
        kwargs = {}
        if self.channel:
            kwargs['channel'] = self.channel

        if self.user:
            kwargs['user'] = self.user

        hist_objects = HistoryDoc.objects(**kwargs)
        hist_list = [Record(r.channel, r.user, r.text, r.time) for r in hist_objects]

        return await self.callback(hist_list)


class UploadCommand(Command):
    def __init__(self, user=None, channel=None, file_name=None, delete=False):
        self.user = user
        self.channel = channel
        self.file_name = file_name
        self.delete = delete

    async def execute(self, slack):
        await slack.upload_file(f_name=self.file_name, channel=self.channel, user=self.user)
        if self.delete:
            os.remove(self.file_name)
