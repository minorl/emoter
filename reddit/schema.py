import db
from mongoengine import Document, FloatField, ListField, ReferenceField, StringField

class RedditUser(Document):
    uname = StringField()
    latest_comment = FloatField()
    latest_post = FloatField()
    comments = ListField(ReferenceField('RedditComment'))
    posts = ListField(ReferenceField('RedditPost'))


class RedditPost(Document):
    post_id = StringField()
    created = FloatField()
    title = StringField()
    text = StringField()

class RedditComment(Document):
    comment_id = StringField()
    created = FloatField()
    link_id = StringField()
    text = StringField()
