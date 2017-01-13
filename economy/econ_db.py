import db
from mongoengine import Document, FloatField, StringField

class AccountDoc(Document):
    user = StringField()
    currency = FloatField()
    meta = {
        'indexes': [
            {
                'fields': ['user'],
                'unique': True
            }
        ]
    }
