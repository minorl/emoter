import abc

class Command(metaclass=abc.ABCMeta):
    pass

class MessageCommand(Command):
    def __init__(self, channel=None, channel_name=None, text=''):
        if not (channel_name is None)  ^ (channel is None):
            raise ValueError("Only one of channel and channel_name may be set")
        self.channel = channel
        self.channel_name = channel_name
        self.text = text
