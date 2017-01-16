from functools import reduce
from operator import or_


from economy import economy
from pyparsing import CaselessLiteral, StringEnd
from slack.bot import SlackBot, register
from slack.command import MessageCommand
from slack.parsing import symbols


class MoneyBot(SlackBot):
    def __init__(self, money_channels, currency_name, slack=None):
        self.currency_name = currency_name

        self.channel_order = money_channels
        # Attribute used for slack API limiting of commands
        self.channels = set(money_channels)

        self.work_commands = {'bootstraps': 0, 'study': 1, 'utilizesynergy': 2}
        self.level_commands = {'college': 0, 'graduate': 1}
        self.level_costs = (500, 10)

        self.check_commands = {'bank': False, 'transcript': True}

        self.check_name = 'Check your status'.format(currency_name)
        self.check_expr = reduce(or_, (CaselessLiteral(s) for s in self.check_commands)).setResultsName('command') + StringEnd()
        self.check_doc = 'Check the amount of {} or grades you have'.format(currency_name)

        self.gain_name = 'Income'
        self.gain_expr = reduce(or_, (CaselessLiteral(s) for s in self.work_commands)).setResultsName('command') + StringEnd()
        self.gain_doc = ('Earn your way through:\n' +
                         '\t{} | {} | {}'.format(*self.work_commands))

        self.level_name = 'Increase your status'
        self.level_expr = reduce(or_, (CaselessLiteral(s) for s in self.level_commands)).setResultsName('command') + StringEnd()
        self.level_doc = ('Work your way up:\n' +
                         '\t{} | {}'.format(*self.level_commands))

        self.give_name = 'Give {}'.format(currency_name)
        self.give_expr = CaselessLiteral('give') + symbols.user_name.setResultsName('user') + symbols.int_num.setResultsName('amount') + StringEnd()
        self.give_doc = 'Create {} in a user\'s account'.format(currency_name)

    @register(name='check_name', expr='check_expr', doc='check_doc')
    async def command_check(self, user, in_channel, parsed):
        secondary = self.check_commands[parsed['command'].lower()]
        money = await economy.user_currency(user, secondary=secondary)
        currency_name = 'grades' if secondary else self.currency_name
        return MessageCommand(
            text='You have {} {}'.format(int(money), currency_name),
            channel=in_channel,
            user=user)

    @register(name='gain_name', expr='gain_expr', doc='gain_doc', channels='channels')
    async def command_gain(self, user, in_channel, parsed):
        level = self.work_commands[parsed['command'].lower()]
        required_channel = self.channel_order[level]

        user_level = await economy.level(user)

        err_message = None
        if user_level < level:
            err_message = 'You can\'t do that yet.'
        elif user_level > level:
            err_message = 'You\'re better than that now.'
        elif required_channel != in_channel:
            err_message = 'None of that in here, go to #{}.'.format(required_channel)
        else:
            if level == 0:
                await economy.give(user, 1)
            elif level == 1:
                await economy.give(user, 1, secondary=True)
            elif level == 2:
                await economy.give(user, 5)

        if err_message:
            return MessageCommand(channel=in_channel, user=user, text=err_message)

    @register(name='level_name', expr='level_expr', doc='level_doc')
    async def command_level(self, user, in_channel, parsed):
        required_level = self.level_commands[parsed['command'].lower()]
        user_level = await economy.level(user)

        secondary = required_level == 1
        cost = self.level_costs[required_level]
        user_currency = await economy.user_currency(user, secondary=secondary)

        if user_level < required_level:
            message = 'You need to pull yourself up by your bootstraps.'
        elif user_level > required_level:
            message = 'You\'ve already done that'
        elif user_currency < cost:
            if secondary:
                message = 'You need {} grades'.format(cost)
            else:
                message = 'You need {} {}. Maybe if you worked harder?'.format(cost, self.currency_name)
        else:
            if secondary:
                await economy.set(user, 0, secondary=True)
                message = 'You\'ve graduated!'
            else:
                await economy.give(user, -cost)
                message = 'You\'ve enrolled!'
            await economy.level_up(user)

        return MessageCommand(channel=in_channel, user=user, text=message)

    @register(name='give_name', expr='give_expr', doc='give_doc', admin=True)
    async def command_give(self, user, in_channel, parsed):
        give_user = parsed['user']
        amount = int(parsed['amount'])
        await economy.give(give_user, amount)
        return MessageCommand(channel=in_channel, user=user, text='Gave {} {} {}'.format(
            give_user, amount, self.currency_name))
