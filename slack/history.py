from mongoengine import DateTimeField, Document, StringField


class HistoryDoc(Document):
    user = StringField()
    channel = StringField()
    text = StringField()
    time = DateTimeField()
