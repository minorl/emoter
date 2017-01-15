from economy import economy
from pyparsing import CaselessLiteral, StringEnd
from slack.bot import SlackBot, register
from slack.command import MessageCommand
from slack.parsing import symbols


class MoneyBot(SlackBot):
    def __init__(self, money_channels, currency_name, slack=None):
        self.currency_name = currency_name

        self.channels = money_channels

        self.check_name = 'Check {}'.format(currency_name)
        self.check_expr = CaselessLiteral('bank') + StringEnd()
        self.check_doc = 'Check the amount of {} you have'

        self.gain_name = 'Income'
        self.gain_expr = CaselessLiteral('bootstraps') + StringEnd()
        self.gain_doc = 'Pull yourself up by your bootstraps'

        self.give_name = 'Give {}'.format(currency_name)
        self.give_expr = CaselessLiteral('give') + symbols.user_name.setResultsName('user') + symbols.int_num.setResultsName('amount') + StringEnd()
        self.give_doc = 'Create {} in a user\'s account'.format(currency_name)

    @register(name='check_name', expr='check_expr', doc='check_doc', channels='channels')
    async def command_check(self, user, in_channel, parsed):
        money = await economy.user_currency(user)
        return MessageCommand(
            text='You have {} {}'.format(int(money), self.currency_name),
            channel=in_channel,
            user=user)

    @register(name='gain_name', expr='gain_expr', doc='gain_doc', channels='channels')
    async def command_gain(self, user, in_channel, parsed):
        if in_channel:
            await economy.give(user, 1)
        else:
            return MessageCommand(
                text='Don\'t be ashamed to work in public',
                user=user)

    @register(name='give_name', expr='give_expr', doc='give_doc', admin=True)
    async def command_give(self, user, in_channel, parsed):
        give_user = parsed['user']
        amount = int(parsed['amount'])
        await economy.give(give_user, amount)
        return MessageCommand(channel=in_channel, user=user, text='Gave {} {} {}'.format(
            give_user, amount, self.currency_name))
