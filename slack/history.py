"""Mongoengine definition for storing history"""
from mongoengine import Document, StringField


class HistoryDoc(Document):
    """A Slack message"""
    user = StringField()
    channel = StringField()
    text = StringField()
    time = StringField()
