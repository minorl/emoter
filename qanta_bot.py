import logging
import re

from slack.bot import SlackBot, register
from slack.command import MessageCommand
from pyparsing import CaselessLiteral, restOfLine
import requests

logger = logging.getLogger(__name__)

def answer_question(text):
    try:
        response = requests.post(
            'http://trantor.entilzha.io:5000/api/answer_question',
            data={'text': text}
        ).json()
        return response['guess'], response['score']
    except Exception as e:
        logger.error('Exception in QANTA: %s', str(e))
        return None


class QantaBot(SlackBot):
    def __init__(self, slack=None):
        self.qanta_name = 'Qanta'
        self.qanta_expr = CaselessLiteral('qanta') + restOfLine()
        self.qanta_doc = 'Answers questions whose answer is a wikipedia page'

    @register(name='qanta_name', expr='qanta_expr', doc='qanta_doc')
    async def command_qanta(self, user, in_channel, parsed):
        text = parsed[1]
        result = answer_question(text)
        if result is None:
            msg = 'Error querying QANTA.'
        else:
            guess, score = result
            msg = 'Is it "{}"? I am {}% confident'.format(
                guess, int(score * 100))
        return MessageCommand(text=msg, user=user, channel=in_channel)
