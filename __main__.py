"""Main module for Slack bot"""
import argparse
import asyncio
import binder_bot
import config
import emote_bot
import haiku_bot
import jeff_bot
from mongoengine import connect
import quote_bot
import react_bot
import sentiment_bot
import twitch_bot
import wordcloud_bot

from slack.slack_api import Slack, SlackConfig
import tensorflow as tf


def main():
    """Instantiate all bots and launch Slack"""

    parser = argparse.ArgumentParser(description='A simple slack bot')
    parser.add_argument('--load_history', action='store_true')
    args = parser.parse_args()
    connect(config.DB_NAME)

    slack_config = SlackConfig(
        token=config.TOKEN,
        alert=config.ALERT,
        name=config.NAME,
        load_history=args.load_history)

    slackapp = Slack(slack_config)
    emote_bot.EmoteBot(channels=config.EMOJI_CHANNELS, slack=slackapp)
    binder_bot.BinderBot(admins=config.ADMINS, max_len=config.MAX_BIND_LEN, slack=slackapp)
    react_bot.ReactBot(
        admins=config.ADMINS,
        out_channels=config.REACTION_CHANNELS,
        max_per_user=config.MAX_REACTS_PER_CHANNEL,
        slack=slackapp)
    quote_bot.QuoteBot(slack=slackapp)
    wordcloud_bot.WordcloudBot(slack=slackapp)
    jeff_bot.JeffBot(emoji_random=config.EMOJI_RANDOM, jeff_bot_target=config.JEFF_BOT_TARGET, jeff_channels=config.JEFF_CHANNELS, slack=slackapp)

    twitch_alias = 'twitch_db'
    connect(config.TWITCH_DB_NAME, alias=twitch_alias)

    twitch_bot.TwitchBot(twitch_alias, min_length=config.MIN_MARKOV_LENGTH, slack=slackapp)

    haiku_bot.HaikuBot(slack=slackapp)

    with tf.Graph().as_default(), tf.Session() as session:
        sentiment_bot.SentimentBot(session=session, slack=slackapp)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(slackapp.run())


if __name__ == '__main__':
    main()
