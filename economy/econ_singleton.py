from asyncio import Lock
from collections import defaultdict

from mongoengine import DoesNotExist
from .econ_db import AccountDoc


def _get_or_create_user(user):
    try:
        return AccountDoc.objects.get(user=user)
    except DoesNotExist:
        obj = AccountDoc(user=user, currency=0, secondary_currency=0, level=0)
        obj.save()
        return obj


class _Economy:
    def __init__(self):
        self._lock = Lock()

        self._ledger = defaultdict(float)
        self._secondary_ledger = defaultdict(float)
        for account in AccountDoc.objects():
            self._ledger[account.user] = account.currency
            self._secondary_ledger[account.user] = account.secondary_currency

    async def give(self, user, amount, secondary=False):
        with await self._lock:
            obj = _get_or_create_user(user)
            currency_attr = 'secondary_currency' if secondary else 'currency'
            obj.update(**{currency_attr: getattr(obj, currency_attr) + amount})
            (self._secondary_ledger if secondary else self._ledger)[user] += amount

    async def set(self, user, amount, secondary=False):
        with await self._lock:
            obj = _get_or_create_user(user)
            obj.update(**{'secondary_currency' if secondary else 'currency': amount})
            (self._secondary_ledger if secondary else self._ledger)[user] = amount

    async def user_currency(self, user, secondary=False):
        with await self._lock:
            return (self._secondary_ledger if secondary else self._ledger)[user]

    async def level(self, user):
        with await self._lock:
            obj = _get_or_create_user(user)
            return obj.level

    async def level_up(self, user):
        with await self._lock:
            obj = _get_or_create_user(user)
            obj.update(level=obj.level + 1)


economy = _Economy()
