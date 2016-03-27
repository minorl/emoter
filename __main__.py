import asyncio
import config
from emotebot import EmoteBot


if __name__ == "__main__":
    bot = EmoteBot(config.TOKEN, 'bot-test')
    loop = asyncio.get_event_loop()
    loop.run_until_complete(bot.main_loop())
