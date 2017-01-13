from asyncio import Lock
from collections import defaultdict

from mongoengine import DoesNotExist
from .econ_db import AccountDoc


def _get_or_create_user(user):
    try:
        return AccountDoc.objects.get(user=user)
    except DoesNotExist:
        obj = AccountDoc(user=user, currency=0)
        obj.save()
        return obj

class _Economy:
    def __init__(self):
        self._lock = Lock()

        self._ledger = defaultdict(float)
        for account in AccountDoc.objects():
            self._ledger[account.user] = account.currency

    async def give(self, user, amount):
        with await self._lock:
            obj = _get_or_create_user(user)
            obj.update(currency=obj.currency + amount)
            self._ledger[user] += amount

    async def user_currency(self, user):
        with await self._lock:
            return self._ledger[user]

economy = _Economy()
