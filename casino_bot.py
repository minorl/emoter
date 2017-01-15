from slack.bot import register, SlackBot
from pyparsing import CaselessLiteral, StringEnd
from slack.parsing import symbols
from slack.command import MessageCommand
from economy import economy
from numpy import random
from pathlib import Path
from casino import casino
from datetime import datetime

class CasinoBot(SlackBot):
    def __init__(self, currency_name, slack=None):
        self.currency_name = currency_name

        self.slots_name = 'Slot machine'
        self.slots_expr = CaselessLiteral('slots') + symbols.int_num.setResultsName('bet') + StringEnd()
        self.slots_doc = ('Gamble away your hard earned {0}:\n\tslots <currency bet>'.format(currency_name))

        self.slots_jackpot_symbol = ':moneybag:'
        self.slots_sym = [':peach:', ':tangerine:', ':cherries:', ':watermelon:', ':banana:', self.slots_jackpot_symbol]
        self.slots_contribution = .45

        self.slots_rig = 'Rig the slot machine'
        self.slots_rig_expr = CaselessLiteral('slots') + symbols.int_num.setResultsName('bet') + symbols.emoji.setResultsName('1')+symbols.emoji.setResultsName('2')+symbols.emoji.setResultsName('3')+ StringEnd()
        self.slots_rig_doc = 'slots <currency bet> <emoji1> <emoji2> <emoji3>'

        self.stats_name = 'Gambling stats'
        self.stats_expr = CaselessLiteral('casino') + CaselessLiteral('stats') + StringEnd()
        self.stats_doc = ('Information on your filthy gambling habits.\n\tcasino stats')

    @register(name='slots_name', expr='slots_expr', doc='slots_doc')
    async def command_slots(self, user, in_channel, parsed):
        return await self.slots(user, in_channel, parsed)

    @register(name='slots_rig', expr='slots_rig_expr', doc='slots_rig_doc', admin=True)
    async def command_slots_jackpot(self, user, in_channel, parsed):
        reels = [parsed['1'], parsed['2'], parsed['3']]
        return await self.slots(user, in_channel, parsed, reels)

    async def slots(self, user, in_channel, parsed, rigged=None):
        bet = int(parsed['bet'])
        bank = await economy.user_currency(user)
        msg = ''
        if bank >= bet:
            reels = rigged if rigged else list(
                random.choice(self.slots_sym, 3))
            jacks = reels.count(self.slots_jackpot_symbol)
            jackpot = False
            if jacks:
                if jacks == 3:
                    won = (await casino.get_jackpot('slots'))
                    jackpot = True
                elif jacks == 2:
                    won = bet * 4
                else:
                    won = 0
            else:
                won = bet * 10 if reels.count(reels[0]) == 3 else 0

            if won or jackpot:  # you can win the jackpot when it's 0...
                # only one command can execute at a time, so no race
                if jackpot:
                    await casino.update_jackpot('slots', - won)
                    await casino.record_win(user, 'slots', won)
                    msg = 'JACKPOT!!!! '
                msg += '{0} won {1} {2}!'.format(user,
                                                 int(won), self.currency_name)
            else:
                msg = 'Try again.'
                await casino.update_jackpot('slots', bet * self.slots_contribution)

            await economy.give(user, won - bet)
            await casino.record(user, 'slots', won - bet)
            return MessageCommand(text='{0}\n{1} Jackpot is {2}.'.format(''.join(reels), msg, int(await casino.get_jackpot('slots'))), channel=in_channel, user=user)
        else:
            return MessageCommand(text='Too poor! Sad.', channel=in_channel, user=user)

    @register(name='stats_name', expr='stats_expr', doc='stats_doc')
    async def command_stats(self, user, in_channel, parsed):
        won, lost, played, jc, jt, jw = await casino.get_stats(user, 'slots')
        msg = '{game} Stats for {user}:\n\tNet *{net}* {currency} (+{won}/{lost}). Played {played} times.\n\tHit {jack} jackpot(s).'
        if jt:
            msg += ' Last jackpot hit was {amount} {currency} at {date:%H:%M:%S %m/%d/%Y} UTC.'
        else:
            jt = datetime.utcnow()
            jw = 0

        formatted = msg.format(user=user, game='Slots', net=int(won+lost), currency=self.currency_name, won=int(won), lost=int(lost),
                               played=played, jack=jc, amount=int(jw), date=jt)

        return MessageCommand(text=formatted, channel=in_channel, user=user)
