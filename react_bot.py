from mongoengine import Document, StringField
from pyparsing import CaselessLiteral
from slack.parsing.symbols import emoji, tail


class ReactDoc(Document):
    regex = StringField()
    reaction = StringField()


class ReactBot:
    def __init__(self, max_per_user=None):
        self.max_per_user = max_per_user

        self.create_name = 'Add a reaction'
        self.create_expr = CaselessLiteral('react') + emoji + tail
