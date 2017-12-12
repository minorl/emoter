from datetime import datetime
from economy import economy
import os
import pickle
from pyparsing import CaselessLiteral, StringEnd, White
from random import random, choice
from slack.bot import SlackBot, register
from slack.command import MessageCommand, ReactCommand
from slack.parsing import symbols
from util import mention_to_uid

SAVE_FILE = 'jeff_save.p'

class JeffBot(SlackBot):
    def __init__(self, probability, emojis, channels, target, dead_user, death_date, slack=None):
        self.channels = channels
        self.pig_name = 'Pig Latin'
        self.pig_expr = CaselessLiteral('pig') + symbols.tail('message') + StringEnd()
        self.pig_doc = ('Translate a message to pig latin:\n'
                           '\tpig <message>')
        self.hankey_name = 'Hankey'
        self.hankey_expr = CaselessLiteral('hankey') + White() + symbols.mention.setResultsName('target') + StringEnd()
        self.hankey_doc = ('Target a user for hankeying:\n'
                           '\thankey <user>')
        self.hankeycost_name = 'Hankey Cost'
        self.hankeycost_expr = CaselessLiteral('hankeycost') + StringEnd()
        self.hankeycost_doc = ('Check the current price of the hankey command:\n'
                           '\thankeycost')
        self.rip_name = 'RIP'
        self.rip_expr = CaselessLiteral('rip') + StringEnd()
        self.rip_doc = ('Check time since %s\'s last appearance:\n'
                           '\trip' % dead_user)
        self.dead_user = dead_user
        self.death_date = datetime.strptime(death_date, "%m/%d/%Y")
        self.target = target
        self.ramoji = emojis
        self.probability = probability
        if os.path.exists(SAVE_FILE):
            with open(SAVE_FILE, 'rb') as f:
                self.cost = pickle.load(f)
        else:
            self.cost = 1
            with open(SAVE_FILE, 'wb') as f:
                pickle.dump(self.cost, f)

    @register(name='rip_name', expr='rip_expr', doc='rip_doc')
    async def command_rip(self, user, in_channel, parsed):
        d1 = self.death_date
        d2 = datetime.now()
        return MessageCommand(text='%s was last seen %s days ago.' % (self.dead_user, (d2-d1).days), channel=in_channel, user=user)

    @register(channels='channels')
    async def command_random(self, user, in_channel, message):
        if random() < self.probability:
            return ReactCommand(choice(self.ramoji))
        else:
            return None

    @register(channels='channels')
    async def command_jeff(self, user, in_channel, message):
        if user == self.target:
            return ReactCommand('hankey')
        else:
            return None

    @register(name='hankeycost_name', expr='hankeycost_expr', doc='hankeycost_doc')
    async def command_hankeycost(self, user, in_channel, parsed):
        return MessageCommand(text='Current cost: %s' % self.cost, channel=in_channel, user=user)

    @register(name='hankey_name', expr='hankey_expr', doc='hankey_doc')
    async def command_hankey(self, user, in_channel, parsed):
        if await economy.user_currency(user) >= self.cost:
            self.target = mention_to_uid(parsed['target'])
            await economy.give(user, -self.cost)
            self.cost += 1
            with open(SAVE_FILE, 'wb') as f:
                pickle.dump(self.cost, f)
        else:
            return MessageCommand(text="no", channel=in_channel, user=user)

    @register(name='pig_name', expr='pig_expr', doc='pig_doc')
    async def command_pig_latin(self, user, in_channel, parsed):
        message = parsed['message']
        return MessageCommand(text=pig_latin(message), channel=in_channel, user=user)

def pig_latin(words):
    vowels = {'a', 'e', 'i', 'o', 'u'}
    new = []
    for word in words.lower().split():
        if word[0] in vowels:
            new.append(word + 'way')
        else:
            start = 0
            for letter in list(word):
                if letter in vowels:
                    break
                else:
                    start += 1
            new.append(word[start:] + word[:start] + 'ay')
    return ' '.join(new)
