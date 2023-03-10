import math
import time
import typing as t

from ellar.cache import ICacheService
from ellar.di import injectable

from .interfaces import IThrottlerStorage
from .throttler_storage_options import ThrottlerStorageOption
from .throttler_storage_record import ThrottlerStorageRecord


@injectable()
class ThrottlerStorageService(IThrottlerStorage):
    def __init__(self) -> None:
        self._storage: t.Dict[str, ThrottlerStorageOption] = {}

    def _set(self, key: str, value: ThrottlerStorageOption) -> None:
        self._storage[key] = value

    def _has_expired(self, key: str) -> bool:
        exp = self._storage.get(key)
        return exp is not None and exp.expires_at <= time.time()

    def _has_key(self, key: str) -> bool:
        return self._get(key) is not None

    def _delete(self, key: str) -> bool:
        try:
            self._storage.pop(key)
        except KeyError:
            return False
        return True

    def _get(self, key: str) -> t.Optional[ThrottlerStorageOption]:
        if self._has_expired(key):
            self._delete(key)
            return None

        return self._storage.get(key)

    @property
    def storage(self) -> t.Dict[str, ThrottlerStorageOption]:
        return self._storage

    def get_expiration_time(self, key: str) -> int:
        return math.floor(self.storage[key].expires_at - time.time())

    async def increment(self, key: str, ttl: int) -> ThrottlerStorageRecord:
        if not self._has_key(key):
            self._set(
                key, ThrottlerStorageOption(total_hits=0, expires_at=time.time() + ttl)
            )

        history = self._get(key)
        assert history, "value can not be None"
        now = time.time()

        time_to_expire = self.get_expiration_time(key)

        if time_to_expire <= 0:
            history.total_hits = 0
            history.expires_at = now + ttl
            time_to_expire = self.get_expiration_time(key)

        history.total_hits += 1

        return ThrottlerStorageRecord(
            total_hits=history.total_hits, time_to_expire=time_to_expire
        )


@injectable()
class CacheThrottlerStorageService(IThrottlerStorage):
    def __init__(self, cache_service: ICacheService) -> None:
        self._cache_service = cache_service

    @property
    def storage(self) -> t.Any:
        return self._cache_service.get_backend()

    async def get_expiration_time(self, key: str) -> int:
        result = await self._cache_service.get_async(f"{key}-ttl")
        return math.floor(result - time.time()) if result else -1

    async def increment(self, key: str, ttl: int) -> ThrottlerStorageRecord:
        if not await self._cache_service.has_key_async(key):
            await self._cache_service.set_async(key, 0, ttl)
            await self._cache_service.set_async(f"{key}-ttl", time.time() + ttl, ttl)

        time_to_expire = await self.get_expiration_time(key)

        if time_to_expire <= 0:
            await self._cache_service.set_async(key, 0, ttl)
            await self._cache_service.set_async(f"{key}-ttl", time.time() + ttl, ttl)
            time_to_expire = await self.get_expiration_time(key)

        total_hits = await self._cache_service.incr_async(key)

        return ThrottlerStorageRecord(
            total_hits=total_hits, time_to_expire=time_to_expire
        )
