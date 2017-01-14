import asyncio
from collections import deque
from league.league_db import GameDoc, PlayerGameDoc, SummonerDoc
from mongoengine import DoesNotExist


class LeagueMonitor:
    def __init__(self, api, monitor_names):
        """
        Arguments:
            api: LeagueApi type
            monitor_users: List of summoner names
        """
        self.api = api
        self.monitor_names = monitor_names

    async def run(self):
        monitor_users = {}
        for s_name, data in (await self.api.get_summoners_info_by_names(self.monitor_names)).items():
            monitor_users[s_name] = data['id']

        known_recent_games = {sname: deque(maxlen=10) for sname in monitor_users}

        for sname, game_deque in known_recent_games.items():
            try:
                obj = SummonerDoc.objects.get(name=sname)
            except DoesNotExist:
                obj = SummonerDoc(name=sname, game_refs=[])
                obj.save()
            for game in obj.game_refs[-10:]:
                game_deque.append(game.game_id)

        while True:
            for sname, game_deque in known_recent_games.items():
                print('Getting games for {}'.format(sname))
                summoner = SummonerDoc.objects.get(name=sname)
                recent_games = (await self.api.get_recent_games(monitor_users[sname]))['games']
                for game in recent_games:
                    game_id = game['gameId']
                    if game['gameType'] != 'MATCHED_GAME' or game_id in game_deque:
                        continue
                    game_deque.append(game_id)

                    game_obj = get_or_create_game(game_id, game['createDate'])
                    stats = game['stats']

                    player_game = PlayerGameDoc(
                        name=sname,
                        kills=stats.get('championsKilled', 0),
                        deaths=stats.get('numDeaths', 0),
                        assists=stats.get('assists', 0),
                        double_kills=stats.get('doubleKills', 0),
                        triple_kills=stats.get('tripleKills', 0),
                        quadra_kills=stats.get('quadraKills', 0),
                        penta_kills=stats.get('pentaKills', 0),
                        champion=await self.api.get_champion_by_id(game['championId']),
                        won=stats['win'])

                    game_obj.update(push__player_games=player_game)
                    summoner.update(push__game_refs=game_obj)

            await asyncio.sleep(600)


def get_or_create_game(game_id, create_date):
    try:
        obj = GameDoc.objects.get(game_id=game_id)
    except DoesNotExist:
        obj = GameDoc(game_id=game_id, create_date=create_date)
        obj.save()
    return obj


def get_recent_games(summoner_name):
    summoner_name = summoner_name.lower()
    return [next(pg for pg in game.player_games if pg.name == summoner_name) for game in SummonerDoc.objects.get(name=summoner_name).game_refs]
