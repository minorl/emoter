from slack.bot import register, SlackBot
from pyparsing import CaselessLiteral, StringEnd
from slack.parsing import symbols
from slack.command import MessageCommand
from economy import economy
from numpy import random
from pathlib import Path

class CasinoBot(SlackBot):
    def __init__(self, currency_name, slack=None):
        self.currency_name = currency_name

        self.slots_name = 'Slot machine'
        self.slots_expr = CaselessLiteral('slots') + symbols.int_num.setResultsName('bet') + StringEnd()
        self.slots_doc = ('Gamble away your hard earned {0}:\n\tslot <currency bet>'.format(currency_name))
        self.slots_jackpot_symbol = ':moneybag:'
        self.slots_sym = [':peach:', ':tangerine:', ':cherries:', ':watermelon:', ':banana:', self.slots_jackpot_symbol]
        self.slots_contribution = .45
        #quick hack to persist jackpot across restarts
        self.slots_jackpot_file = Path('jackpot.txt')
        if self.slots_jackpot_file.is_file():
            self.slots_jackpot = float(self.slots_jackpot_file.read_text())
        else:
            self.slots_jackpot_file.write_text('0')
            self.slots_jackpot = 0


    @register(name='slots_name', expr='slots_expr', doc='slots_doc')
    async def command_slots(self, user, in_channel, parsed):
        bet = int(parsed['bet'])
        bank = await economy.user_currency(user)
        msg = ''
        if bank >= bet:
            reels = list(random.choice(self.slots_sym, 3))
            jacks = reels.count(jackpot)
            if jacks:
                won = self.slots_jackpot if jacks == 3 else bet * 4 if jacks == 2 else 0
            else:
                won = bet * 10 if reels.count(reels[0]) == 3 else 0
            
            if won:
                if won == self.slots_jackpot:
                    self.update_jackpot(-won)
                    msg = 'JACKPOT!!!!'
                msg += 'You won {0} {1}!'.format(won, self.currency_name)
            else:
                msg = 'You lose.'
                self.update_jackpot(bet * self.slots_contribution)
            await economy.give(user, won - bet)
            return MessageCommand(text='{0}\n{1} Jackpot is {2}.'.format(''.join(reels), msg, int(self.slots_jackpot)), channel=in_channel, user=user)
        else:
            return MessageCommand(text='Too poor!', channel=in_channel, user=user)

    def update_jackpot(self, amount):
        self.slots_jackpot += amount
        self.slots_jackpot_file.write_text(str(self.slots_jackpot))
