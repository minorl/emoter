"""Metaprogramming to support registering slack bots"""
from collections import namedtuple
from functools import partial, wraps
from .slack_api import Slack

HandlerData = namedtuple('HandlerData', ['name', 'expr', 'channels', 'doc', 'priority', 'admin', 'include_timestamp'])


class SlackHandler:
    """
    Wrapper to store some data along with a function.
    A class is necessary to allow the original function to still be callable directly.
    """
    def __init__(self, func, data):
        self._func = func
        self._data = data

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    @property
    def data(self):
        """Accessor for data which is of type HandlerData"""
        return self._data

    @property
    def func(self):
        """Accessor for func"""
        return self._func


def register(name=None, expr=None, channels=None, doc=None, priority=0, admin=False, include_timestamp=False):
    """
    Decorator for registering a function to be a slack handler.
    Must be used on a method in a class which inherits from SlackBot.
    """
    def wrap(f):
        """Create SlackHandler with f. Uses wraps to preseve metadata."""
        return wraps(f)(SlackHandler(f, HandlerData(name, expr, channels, doc, priority, admin, include_timestamp)))
    return wrap


class SlackBotMeta(type):
    """Metaclass for SlackBot"""
    def __init__(cls, name, bases, cls_dict):
        super().__init__(name, bases, cls_dict)
        names = [a for a, val in cls_dict.items() if isinstance(val, SlackHandler)]

        def new_init(self, *args, **kwargs):
            """Replaces __init__ on SlackBot. Loads all handlers."""
            slack = kwargs.get('slack', None)
            if not isinstance(slack, Slack):
                raise TypeError(
                    ('Function __init__ of a class which inherits from SlackBot'
                     'must receive a keyword argument "slack" of type Slack.'))

            cls_dict['__init__'](self, *args, **kwargs)
            for name in names:
                handler = getattr(self, name)
                func = partial(handler.func, self)
                data = handler.data

                name = getattr(self, data.name) if data.name else ''
                expr = getattr(self, data.expr) if data.expr else None
                channels = getattr(self, data.channels) if data.channels else None
                doc = getattr(self, data.doc) if data.doc else ''
                mapped_data = HandlerData(
                    name=name,
                    expr=expr,
                    channels=channels,
                    doc=doc,
                    priority=data.priority,
                    admin=data.admin,
                    include_timestamp=data.include_timestamp)

                slack.register_handler(func, mapped_data)
        setattr(cls, '__init__', new_init)


class SlackBot(metaclass=SlackBotMeta):
    """Class to inherit from when making Slack bots"""
    def __init__(self, *args, **kwargs):
        pass
