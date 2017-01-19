import db
from mongoengine import (BooleanField, DictField, Document, EmbeddedDocument,
    EmbeddedDocumentListField, IntField, ListField, LongField, MapField, ReferenceField, StringField)


class PlayerGameDoc(EmbeddedDocument):
    name = StringField()
    kills = IntField()
    deaths = IntField()
    assists = IntField()
    double_kills = IntField()
    triple_kills = IntField()
    quadra_kills = IntField()
    penta_kills = IntField()
    champion = StringField()
    won = BooleanField()


class GameDoc(Document):
    game_id = LongField()
    create_date = LongField()

    player_games = EmbeddedDocumentListField(PlayerGameDoc)
    meta = {
        'indexes': [
            {
                'fields': ['game_id'],
                'unique': True
            }
        ]
    }


class SummonerDoc(Document):
    name = StringField()
    game_refs = ListField(ReferenceField('GameDoc'))
