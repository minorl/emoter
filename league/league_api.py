"""Modified from code by irakliz on Github"""
import asyncio
from collections import deque
import json
import os
import requests
import time
import util

retry_errors = [429, 500, 503]  # Rate limit exceeded, Internal server error, Service unavailable


class NotFoundException(Exception):
    pass


BASE_URL = "https://na.api.pvp.net/api/lol/"
REGION = "na"
FAST_RATE_LIMIT = 10  # per 10 seconds
SLOW_RATE_LIMIT = 500  # per 600 seconds


class LeagueApi:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_summoner_url = '{}{}/v1.4/summoner/'.format(BASE_URL, REGION)

        self.base_game_url = '{}{}/v1.3/game/by-summoner/{}/recent'.format(BASE_URL, REGION, '{}')
        self.base_match_url = '{}{}/v2.2/match/{}'.format(BASE_URL, REGION, '{}')
        self.base_current_url = 'https://na.api.pvp.net/observer-mode/rest/consumer/getSpectatorGameInfo/%s/%d'
        self.champion_url = '{}static-data/{}/v1.2/champion'.format(BASE_URL, REGION)

        # Seeding deques with time 0 so making a request will always be valid until they are full
        self.fast_deque = deque([0], maxlen=FAST_RATE_LIMIT)
        self.slow_deque = deque([0], maxlen=SLOW_RATE_LIMIT)
        self.champions = {}

        self.request_lock = asyncio.Lock()

    async def _get(self, url):
        while True:
            with await self.request_lock:
                now = time.time()
                if now - self.fast_deque[0] > 10 and now - self.slow_deque[0] > 600:
                    url_auth = ('{}?api_key={}'.format(url, self.api_key))
                    loop = asyncio.get_event_loop()
                    request_info = await loop.run_in_executor(None, requests.get, url_auth)

                    now = time.time()
                    self.fast_deque.append(now)
                    self.slow_deque.append(now)
                    break
            await asyncio.sleep(5)

        # print('Url: {} Status: {}'.format(url_auth, request_info.status_code))
        if request_info.status_code in retry_errors:
            return None
        elif request_info.status_code == 404:
            raise NotFoundException('Request was not found')
        elif request_info.status_code != 200:
            raise ValueError(request_info.status_code)

        return json.loads(request_info.text)

    async def get(self, url):
        result = await self._get(url)
        while result is None:
            await asyncio.sleep(5)
            result = await self._get(url)
        return result

    async def get_summoners_info_by_names(self, summoner_names):
        """Get info about summoners by summoner names

        Keyword arguments:
        summoner_names -- list of summoner names to query
        """
        results = []
        for subset in util.grouper(summoner_names, 40):
            url = self.base_summoner_url + 'by-name/' + ','.join(name for name in subset if name)
            results.append(await self.get(url))

        return util.dict_merge(results)

    async def get_summoners_info_by_ids(self, summoner_ids):
        """Get info about summoners by summoner ids

        Keyword arguments:
        summoner_ids -- list of summoner ids to query
        """

        results = []
        for subset in util.grouper(summoner_ids, 40):
            url = self.base_summoner_url + ','.join(str(summoner_id) for summoner_id in subset if summoner_id)
            results.append(await self.get(url))

        return util.dict_merge(results)

    async def get_summoner_names_by_ids(self, summoner_ids):
        """Get summoner names by their ids

        Keyword arguments:
        summoner_ids -- list of summoner ids to query
        """
        results = []
        for subset in util.grouper(summoner_ids, 40):
            url = self.base_summoner_url + ','.join(str(summoner_id) for summoner_id in subset if summoner_id) + '/name'
            results.append(await self.get(url))

        return util.dict_merge(results)

    async def get_recent_games(self, summoner_id):
        """Get 10 most recent games of a summoner

        Keyword arguments:
        summoner_id -- summoner id for querying the recent games
        """

        url = self.base_game_url.format(summoner_id)
        return await self.get(url)

    async def get_match_info(self, match_id):
        """Get detailed info about a match

        Keyword arguments:
        match_id -- id of the match
        """

        url = self.base_match_url.format(match_id)
        return await self.get(url)

    async def get_current_match(self, summoner_id):
        """Get detailed info about a the current ongoing match

        Keyword arguments:
        summoner_id -- id of the summoner
        """

        url = self.base_current_url.format('NA1', summoner_id)
        return await self.get(url)

    async def get_champion_by_id(self, champion_id):
        if champion_id not in self.champions:
            champ_data = await self.get(self.champion_url)
            for champion, data in champ_data['data'].items():
                self.champions[data['id']] = champion
