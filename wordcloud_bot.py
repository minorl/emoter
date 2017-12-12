from functools import partial
import numpy as np
import os
from PIL import Image
from pyparsing import CaselessLiteral, Optional, StringEnd
import re
import requests
import shutil
from slack.bot import register, SlackBot
from slack.command import HistoryCommand, MessageCommand, UploadCommand
from slack.parsing import symbols
from wordcloud import WordCloud, STOPWORDS, ImageColorGenerator
import tempfile
from util import get_image, mention_to_uid

class WordcloudBot(SlackBot):
    def __init__(self, slack):
        self.name = 'Display a wordcloud'
        self.expr = (CaselessLiteral('wordcloud') +
                     (Optional(symbols.flag_with_arg('user', symbols.mention)) &
                      Optional(symbols.flag_with_arg('channel', symbols.channel_name)) &
                      Optional(symbols.flag('all_channels')) &
                      Optional(symbols.flag_with_arg('image', symbols.link))
                      ) + StringEnd()
                     )

        self.doc = ('Make a wordcloud using chat history, with optional filters:\n'
                    '\twordcloud [--user <user>] [--channel <channel> | --all_channels] [--image <image>]')

    @register(name='name', expr='expr', doc='doc')
    async def command_wordcloud(self, user, in_channel, parsed):
        kwargs = {}
        if 'user' in parsed:
            kwargs['user'] = mention_to_uid(parsed['user'])

        if 'all_channels' in parsed:
            pass
        elif 'channel' in parsed:
            kwargs['channel'] = parsed['channel']
        else:
            kwargs['channel'] = in_channel
        kwargs['callback'] = partial(self._history_handler,
                                     user,
                                     in_channel,
                                     parsed['image'][1:-1] if 'image' in parsed else None)
        return HistoryCommand(**kwargs)

    async def _history_handler(self, user, in_channel, image_url, hist_list):
        if not hist_list:
            return
        try:
            image_file = await get_image(image_url) if image_url else None
        except ValueError:
            return MessageCommand(channel=None, user=user, text='Image {} not found.'.format(image_url))

        text = (rec.text for rec in hist_list)
        # Leslie's regex for cleaning mentions, emoji and uploads
        text = (re.sub('<[^>]*>|:[^\s:]*:|uploaded a file:', '', t) for t in text)

        try:
            out_file = await WordcloudBot.make_wordcloud(' '.join(text), image_file)
        except NotImplementedError as e:
            return MessageCommand(channel=None, user=user, text="Apparently can't handle that image: {}".format(e.message()))
        return UploadCommand(channel=in_channel, user=user, file_name=out_file, delete=True)

    @staticmethod
    async def make_wordcloud(text, image_file=None):
        kwargs = {}
        if image_file:
            ttd_coloring = np.array(Image.open(image_file))
            kwargs['mask'] = ttd_coloring
            kwargs['color_func'] = ImageColorGenerator(ttd_coloring)

        # TODO: Turn some of the options into flags
        wc = WordCloud(background_color='white',
                       max_words=2000,
                       stopwords=STOPWORDS,
                       max_font_size=40,
                       random_state=42,
                       **kwargs)

        wc.generate(text)
        # TODO: Replace this with a tempfile
        name = next(tempfile._get_candidate_names()) + '.png'
        wc.to_file(name)

        if image_file:
            os.remove(image_file)
        return name

