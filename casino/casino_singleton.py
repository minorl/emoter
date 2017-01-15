from asyncio import Lock
from collections import defaultdict

from mongoengine import DoesNotExist
from .casino_db import ScoreboardDoc, GameDoc, BigWinsHistoryDoc


def _get_or_create_scoreboard_user(user, game):
    try:
        return ScoreboardDoc.objects.get(user=user)
    except DoesNotExist:
        obj = ScoreboardDoc(user=user, game=game)
        obj.save()
        return obj

def _get_or_create_game(game):
    try:
        return GameDoc.objects.get(game=game)
    except DoesNotExist:
        obj = GameDoc(game=game, jackpot=0.0)
        obj.save()
        return obj


class _Casino:
    def __init__(self):
        self._lock = Lock()

        self._games = defaultdict(lambda: defaultdict(float))
        self._jackpot = defaultdict(float)
        for score in ScoreboardDoc.objects():
            self._games[score.game][score.user] = score.won + score.lost
        for game in GameDoc.objects():
            self._jackpot[game.game] = game.jackpot

    async def record(self, user, game, amount):
        with await self._lock:
            obj = _get_or_create_scoreboard_user(user, game)
            if amount > 0:
                obj.update(won=obj.won + amount, played=obj.played + 1)
            else:
                obj.update(lost=obj.lost + amount, played=obj.played + 1)
            self._games[game][user] += amount

    async def standing(self, user, game):
        with await self._lock:
            return self._slots[game][user]

    async def update_jackpot(self, game, amount):
        with await self._lock:
            obj = _get_or_create_game(game)
            obj.update(jackpot=obj.jackpot + amount)
            self._jackpot[game] += amount

    async def get_jackpot(self, game):
        with await self._lock:
            return self._jackpot[game]

    async def record_win(self, user, game, amount):
        obj = BigWinsHistoryDoc(game=game, user=user, winnings=amount)
        obj.save()

    async def get_stats(self, user, game):
        with await self._lock:
            obj = _get_or_create_scoreboard_user(user, game)
            jackpots = BigWinsHistoryDoc.objects(game=game, user=user)
            j = jackpots.first()
            return(obj.won, obj.lost, obj.played, jackpots.count(), j and j.time, j and j.winnings)

casino = _Casino()
