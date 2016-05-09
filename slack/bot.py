from collections import namedtuple
from .slack_api import Slack


HandlerData = namedtuple('HandlerData', ['name', 'expr', 'channels', 'doc', 'priority'])


def register(name=None, expr=None, channels=None, doc=None, priority=0):
    if not expr:
        raise ValueError("Must specify an expression")

    def wrap(f):
        f._slack_handler_data = HandlerData(name, expr, channels, doc, priority)
        return f

    return wrap


class SlackBotMeta(type):
    def __init__(cls, name, bases, cls_dict):
        super().__init__(name, bases, cls_dict)
        names = [a for a, val in cls_dict.items() if hasattr(val, '_slack_handler_data')]

        def new_init(self, *args, **kwargs):
            slack = kwargs.get('slack', None)
            if not isinstance(slack, Slack):
                raise TypeError('Function __init__ of a class which inherits from SlackBot must have a keyword argument "slack" of type Slack.')

            cls_dict['__init__'](self, *args, **kwargs)
            for name in names:
                f = getattr(self, name)
                data = f._slack_handler_data
                slack.register_handler(name=getattr(self, data.name) if data.name else '',
                                       expr=getattr(self, data.expr),
                                       doc=getattr(self, data.doc) if data.doc else '',
                                       func=f,
                                       channels=getattr(self, data.channels) if data.channels else None,
                                       priority=data.priority)
        setattr(cls, '__init__', new_init)


class SlackBot(metaclass=SlackBotMeta):
    def __init__(self, *args, channels, **kwargs):
        self.channels = channels
