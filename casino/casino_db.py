"""Documents used in the casino"""

import db
from mongoengine import DictField, Document, FloatField, IntField, ListField, LongField, StringField, DateTimeField
from datetime import datetime

class ScoreboardDoc(Document):
    """Document representing a user's wins/losses for a game"""
    user = StringField(required=True)
    game = StringField(required=True)
    won = FloatField(default=0)
    lost = FloatField(default=0)
    played = IntField(default=0)
    meta = {
        'indexes':[
            {
                'fields': ['user'],
                'unique': True
            }
        ]
    }

class CasinoGameDoc(Document):
    """Document representing a casino game"""
    game = StringField()
    jackpot = FloatField()
    meta = {
        'indexes':[
            {
                'fields': ['game'],
                'unique': True
            }
        ]
    }

class BigWinsHistoryDoc(Document):
    """Document representing jackpot payouts"""
    game = StringField()
    time = DateTimeField(default=datetime.utcnow) #yuck timezones
    user = StringField()
    winnings = FloatField()
    meta ={
        'ordering': ['-time']
    }
