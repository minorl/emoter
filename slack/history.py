from mongoengine import Document, StringField


class HistoryDoc(Document):
    user = StringField()
    channel = StringField()
    text = StringField()
    time = StringField()
