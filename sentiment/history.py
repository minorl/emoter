from mongoengine import Document, FloatField, StringField


class SentimentDoc(Document):
    """Records the sentiment of a slack message"""
    time = StringField(required=True, unique=True)
    user = StringField()
    channel = StringField()
    pos_sent = FloatField()
    neut_sent = FloatField()
    neg_sent = FloatField()
    meta = {
        'indexes': [{
            'fields': ['time'],
            'unique': True
        }]
    }
