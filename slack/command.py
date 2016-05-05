import abc

class Command(metaclass=abc.ABCMeta):
    pass

class MessageCommand(Command):
    def __init__(self, channel=None, user=None, text=''):
        self.channel = channel
        self.user = user
        self.text = text
