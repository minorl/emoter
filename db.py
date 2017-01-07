import config
from mongoengine import connect

connect(config.DB_NAME)
