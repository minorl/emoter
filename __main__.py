"""Main module for Slack bot"""
import argparse
import asyncio
import binder_bot
import config
import db
import emote_bot
import face_replace_bot
import frog_bot
import haiku_bot
import jeff_bot
import markov_bot
import money_bot
from mongoengine import connect
from league.league_api import LeagueApi
from league.monitor import LeagueMonitor
import quote_bot
import react_bot
import sentiment_bot
import stock_bot
import twitch_bot
import wordcloud_bot
import casino_bot
from util import handle_async_exception

from slack.slack_api import Slack, SlackConfig
import tensorflow as tf


def main():
    """Instantiate all bots and launch Slack"""

    parser = argparse.ArgumentParser(description='A simple slack bot')
    parser.add_argument('--load_history', action='store_true')
    parser.add_argument('--clear_commands', action='store_true')
    args = parser.parse_args()

    slack_config = SlackConfig(
        token=config.TOKEN,
        admin_token=config.ADMIN_TOKEN,
        alert=config.ALERT,
        name=config.NAME,
        load_history=args.load_history,
        clear_commands=args.clear_commands,
        admins=config.ADMINS)

    slackapp = Slack(slack_config)

    emote_bot.EmoteBot(channels=config.EMOJI_CHANNELS, slack=slackapp)
    binder_bot.BinderBot(admins=config.ADMINS, max_len=config.MAX_BIND_LEN, slack=slackapp)
    frog_bot.FrogBot(config.FROG_CHANNELS, slack=slackapp)
    react_bot.ReactBot(
        admins=config.ADMINS,
        out_channels=config.REACTION_CHANNELS,
        max_per_user=config.MAX_REACTS_PER_CHANNEL,
        slack=slackapp)
    quote_bot.QuoteBot(slack=slackapp)
    wordcloud_bot.WordcloudBot(slack=slackapp)
    jeff_bot.JeffBot(
        probability=config.JEFF_BOT_PROBABILITY,
        emojis=config.JEFF_BOT_EMOJIS,
        target=config.JEFF_BOT_TARGET,
        dead_user=config.JEFF_DEAD_USER,
        death_date=config.JEFF_DEATH_DATE,
        channels=config.JEFF_CHANNELS,
        slack=slackapp)

    markov_bot.MarkovBot(slack=slackapp)
    money_bot.MoneyBot(config.MONEY_CHANNELS, config.MONEY_NAME, slack=slackapp)

    s_bot = stock_bot.StockBot(
        stock_users=config.STOCK_USERS,
        currency_name=config.MONEY_NAME,
        timezone=config.TIMEZONE,
        index_name=config.INDEX_NAME,
        slack=slackapp)
    loop = asyncio.get_event_loop()
    loop.create_task(handle_async_exception(s_bot.dividend_loop))

    twitch_alias = 'twitch_db'
    connect(config.TWITCH_DB_NAME, alias=twitch_alias)

    twitch_bot.TwitchBot(twitch_alias, min_length=config.MIN_MARKOV_LENGTH, slack=slackapp)

    haiku_bot.HaikuBot(slack=slackapp)
    face_replace_bot.FaceReplaceBot(slack=slackapp)
    casino_bot.CasinoBot(config.MONEY_NAME, slack=slackapp)

    # League stuff
    league_api = LeagueApi(config.LEAGUE_KEY)
    league_monitor = LeagueMonitor(league_api, monitor_names=list(config.STOCK_USERS.values()))

    with tf.Graph().as_default(), tf.Session() as session:
        sentiment_bot.SentimentBot(session=session, slack=slackapp)
        loop = asyncio.get_event_loop()
        # loop.create_task(handle_async_exception(league_monitor.run))
        loop.run_until_complete(slackapp.run())


if __name__ == '__main__':
    main()
