"""Documents used in the fake economy"""

import db  # pylint: disable=unused-import
from mongoengine import DictField, Document, FloatField, IntField, ListField, LongField, StringField


class AccountDoc(Document):
    """Document representing a user's currency"""
    user = StringField()
    currency = FloatField()
    secondary_currency = FloatField()
    level = IntField(default=0)
    meta = {
        'indexes': [
            {
                'fields': ['user'],
                'unique': True
            }
        ]
    }


class StockDoc(Document):
    """Document representing a stock and how much of it is held by the central store"""
    name = StringField()
    target_user = StringField()
    dividend_history = ListField(FloatField())
    last_dividend_time = LongField()
    quantity = IntField()
    total = IntField()
    meta = {
        'indexes': [
            {
                'fields': ['target_user'],
                'unique': True
            },
            {
                'fields': ['name'],
                'unique': True
            }
        ]
    }


class StockHoldingsDoc(Document):
    """Document which tracks which stocks a user has"""
    user = StringField()
    stocks = DictField()
