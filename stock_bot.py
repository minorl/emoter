import asyncio
from datetime import datetime
from operator import itemgetter
import time

from economy.econ_db import StockDoc, StockHoldingsDoc
from economy.econ_singleton import economy
from league.monitor import get_recent_games
from mongoengine import DoesNotExist
import numpy as np
from pyparsing import alphas, CaselessLiteral, nums, Optional, StringEnd, Word
from slack.bot import register, SlackBot
from slack.command import MessageCommand
from slack.parsing import symbols
from util import handle_async_exception


class StockBot(SlackBot):
    def __init__(
            self,
            stock_users,
            currency_name,
            index_name,
            timezone,
            min_count=100,
            max_count=500,
            points_per_death=15,
            payout_hours=6,
            min_payoff_period_days=4,
            max_payoff_period_days=21,
            slack=None):
        current = set(stock.target_user for stock in StockDoc.objects())
        now = datetime.now()
        last_dividend_time = now.replace(minute=0, second=0, microsecond=0, hour=now.hour // payout_hours * payout_hours).timestamp()
        valid_letters = {c for c in alphas.upper() if c not in 'AEIOU'}
        for user in stock_users:
            if user not in current:
                total = int(np.random.uniform(low=min_count, high=max_count))
                name = ''.join(c for c in user.upper() if c in valid_letters)[:4]
                StockDoc(
                    target_user=user,
                    name=name,
                    quantity=total,
                    total=total,
                    last_dividend_time=last_dividend_time
                    ).save()

        self.payout_hours = payout_hours
        self.next_dividend_time = last_dividend_time + payout_hours * 3600
        self.timezone = timezone
        self.payoff_scale_factor = max_payoff_period_days - min_payoff_period_days
        self.payoff_offset = min_payoff_period_days
        self.points_per_death = points_per_death

        self.check_name = 'Check Stocks'
        self.check_expr = CaselessLiteral('portfolio') + StringEnd()
        self.check_doc = 'Check your stock inventory:\n\tportfolio'

        self.info_name = 'Stock Info'
        self.info_expr = CaselessLiteral('info') + symbols.user_name.setResultsName('stock') + StringEnd()
        self.info_doc = ('Check prices, inventory and dividends for a stock:\n'
                         '\tinfo <stock>')

        self.available_name = 'Available Stocks'
        self.available_expr = CaselessLiteral('ticker') + StringEnd()
        self.available_doc = ('See what stocks are available:\n'
                              '\tticker')

        self.index_name = index_name
        self.index_expr = CaselessLiteral('index') + StringEnd()
        self.index_doc = ('Check the {}:\n'
                          '\tindex').format(index_name)

        self.buy_name = 'Buy Stocks'
        self.buy_expr = (CaselessLiteral('buy') +
                         Optional(symbols.flag_with_arg('amount', Word(nums))) +
                         symbols.user_name.setResultsName('stock'))
        self.buy_doc = 'Buy stocks for {}:\n\tbuy <stock>'.format(currency_name)

        self.sell_name = 'Sell Stocks'
        self.sell_expr = (CaselessLiteral('sell') +
                          Optional(symbols.flag_with_arg('amount', Word(nums))) +
                          symbols.user_name.setResultsName('stock'))
        self.sell_doc = 'Sell stocks for {}:\n\tsell <stock>'.format(currency_name)

        self.dividend_name = 'Give dividend on demand'
        self.dividend_expr = CaselessLiteral('dividend') + StringEnd()
        self.dividend_doc = ('Pay dividend immediately for all stocks. Does not delay next dividend:\n'
                             '\tdividend')

        self.currency_name = currency_name
        self.name_to_sname = stock_users

    @register(name='check_name', expr='check_expr', doc='check_doc')
    async def check_stocks(self, user, in_channel, parsed):
        user_obj = get_or_create_user(user)
        stocks = user_obj.stocks
        total_dividend = 0
        for stock_name, amount in stocks.items():
            stock_obj = StockDoc.objects.get(name=stock_name)
            dividend = self.compute_dividend(stock_obj)
            total_dividend += amount * dividend

        lines = []
        lines.extend('`{}{}`: {}'.format(stock, ' ' * (4 - len(stock)), amount) for stock, amount in sorted(stocks.items()))
        lines.append('Your next dividend payment will be {} {}.'.format(int(total_dividend), self.currency_name))

        return MessageCommand(user=user, channel=in_channel, text='\n'.join(lines))

    @register(name='info_name', expr='info_expr', doc='info_doc')
    async def stock_info(self, user, in_channel, parsed):
        stock_name = parsed['stock'].upper()
        try:
            if stock_name == 'all':
                stocks = StockDoc.objects()
            else:
                stocks = [StockDoc.objects.get(name=stock_name)]
        except DoesNotExist:
            return MessageCommand(channel=in_channel, user=user, text='Stock {} does not exist'.format(stock_name))

        for stock in stocks:
            result = []
            dividend = self.compute_dividend(stock)
            buy_price = self.compute_price(dividend, stock)
            sell_price = self.compute_price(dividend, stock, sell=True)
            result.append('*{}* ({} deaths) - Dividend: {:.01f} {} - Price: {} {} - Shares {}/{} ({:.0%})'.format(stock.name, self.get_deaths(stock.target_user), dividend, self.currency_name, sell_price, self.currency_name, stock.quantity, stock.total, stock.quantity/stock.total))
        return MessageCommand(user=user, channel=in_channel, text='\n'.join(result))

    @register(name='available_name', expr='available_expr', doc='available_doc')
    async def available_stocks(self, user, in_channel, parsed):
        result = []
        stock_dividends = [(int(self.compute_price(self.compute_dividend(stock), stock)), stock) for stock in StockDoc.objects()]
        stock_dividends.sort(reverse=True, key=itemgetter(0))
        for price, stock in stock_dividends:
            result.append('*{}* {}'.format(stock.name, price))
        out_message = (' | '.join(result) + '\n' + datetime.fromtimestamp(self.next_dividend_time)
            .strftime('Next dividend %c {}').format(self.timezone))
        return MessageCommand(user=user, channel=in_channel, text=out_message)

    @register(name='index_name', expr='index_expr', doc='available_doc')
    async def market_index(self, user, in_channel, parsed):
        total_dividend = 0
        stock_objs = list(StockDoc.objects())
        for stock in stock_objs:
            total_dividend += self.compute_dividend(stock) * stock.total
        return MessageCommand(
            channel=in_channel,
            user=user,
            text='The {} is at {}'.format(self.index_name, int(total_dividend / len(stock_objs))))

    @register(name='buy_name', expr='buy_expr', doc='buy_doc')
    async def buy_stocks(self, user, in_channel, parsed):
        err_message = None
        stock_name = parsed['stock'].upper()
        try:
            stock = StockDoc.objects.get(name=stock_name)
        except DoesNotExist:
            err_message = 'Stock {} not found'.format(stock_name)

        if not err_message:
            amount = max(int(parsed['amount']), 1) if 'amount' in parsed else 1

            if stock.target_user == user:
                err_message = 'You cannot buy stock in yourself.'
            elif stock.quantity < amount:
                err_message = 'Not enough stocks in stock.'
            else:
                dividend = self.compute_dividend(stock)
                cost = self.compute_price(dividend, stock, amount=amount)
                if await economy.user_currency(user) < cost:
                    err_message = 'You are too poor.'

        if err_message:
            return MessageCommand(user=user, channel=in_channel, text=err_message)

        stock.update(quantity=stock.quantity - amount)

        user_stocks = get_or_create_user(user)

        stock_amounts = user_stocks.stocks
        stock_amounts[stock_name] = stock_amounts.get(stock_name, 0) + amount
        user_stocks.update(stocks=stock_amounts)

        await economy.give(user, -cost)
        return MessageCommand(channel=in_channel, user=user, text='{} bought {} share{} of {} for {} {}.'.format(
            user, amount, 's' if amount > 1 else '', stock_name, cost, self.currency_name))

    @register(name='sell_name', expr='sell_expr', doc='sell_doc')
    async def sell_stocks(self, user, in_channel, parsed):
        err_message = None
        stock_name = parsed['stock'].upper()
        try:
            stock = StockDoc.objects.get(name=stock_name)
        except DoesNotExist:
            err_message = 'Stock {} not found'.format(stock_name)

        if not err_message:
            amount = max(int(parsed['amount']), 1) if 'amount' in parsed else 1
            user_holdings = StockHoldingsDoc.objects.get(user=user)
            stock_amounts = user_holdings.stocks
            if stock_amounts[stock_name] < amount:
                err_message = 'You do not have enough stock to fulfill that sale.'
            else:
                dividend = self.compute_dividend(stock)
                money = self.compute_price(dividend, stock, amount=amount, sell=True)
                await economy.give(user, money)

                stock.update(quantity=stock.quantity + amount)
                stock_amounts[stock_name] -= amount
                if stock_amounts[stock_name] == 0:
                    del stock_amounts[stock_name]
                user_holdings.update(stocks=stock_amounts)

        if err_message:
            return MessageCommand(channel=in_channel, user=user, text=err_message)

    @register(name='dividend_name', expr='dividend_expr', doc='dividend_doc', admin=True)
    async def command_dividend(self, in_channel, user, parsed):
        await self.pay_dividends()

    def compute_price(self, dividend, stock, amount=1, sell=False):
        # First term is number of hours needed to pay off
        total = 0
        quantity = stock.quantity + sell
        for i in range(amount):
            payoff_time = self.payoff_scale_factor * ((quantity / stock.total) - 1) ** 2 + self.payoff_offset
            total += int((payoff_time * 24 / self.payout_hours) * dividend)
            quantity += 1 if sell else -1
        return total

    def compute_dividend(self, stock):
        return (1 + self.points_per_death * self.get_deaths(stock.target_user)) / stock.total

    def get_deaths(self, target_user):
        games = get_recent_games(self.name_to_sname[target_user])
        total_deaths = sum(g.deaths for g in games)
        if len(games) < 10 and games:
            total_deaths = int(total_deaths / len(games) * 10)
        return total_deaths

    async def dividend_loop(self):
        payout_seconds = self.payout_hours * 3600
        while True:
            await asyncio.sleep(int(self.next_dividend_time - time.time()))
            self.next_dividend_time += payout_seconds
            await self.pay_dividends()

    async def pay_dividends(self):
        for stock in StockDoc.objects():
            name = stock.name
            dividend = self.compute_dividend(stock)
            for holdings in StockHoldingsDoc.objects():
                if name in holdings.stocks:
                    await economy.give(holdings.user, holdings.stocks[name] * dividend)
            stock.update(last_dividend_time=time.time())
            stock.update(push__dividend_history=dividend)


def get_or_create_user(user):
    try:
        return StockHoldingsDoc.objects.get(user=user)
    except DoesNotExist:
        new_obj = StockHoldingsDoc(user=user, stocks={})
        new_obj.save()
        return new_obj
