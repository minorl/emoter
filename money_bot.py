from economy import economy
from pyparsing import CaselessLiteral, StringEnd
from slack.bot import SlackBot, register
from slack.command import MessageCommand

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

    @register(name='check_name', expr='check_expr', doc='check_doc', channels='channels')
    async def command_check(self, user, in_channel, parsed):
        money = await economy.user_currency(user)
        return MessageCommand(
            text='You have {} {}'.format(int(money), self.currency_name),
            channel=in_channel,
            user=user)

    @register(name='gain_name', expr='gain_expr', doc='gain_doc', channels='channels')
    async def command_gain(self, user, in_channel, parsed):
        await economy.give(user, 1)
