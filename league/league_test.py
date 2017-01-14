import asyncio
from config import LEAGUE_KEY
from league.league_api import LeagueApi


async def get_summ(api):
    for i in range(100):
        print(await api.get_summoners_info_by_names(['ThatSpysASpy']))

if __name__ == '__main__':
    api = LeagueApi(LEAGUE_KEY)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(get_summ(api))
