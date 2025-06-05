import functools
import pickle
import re
from typing import cast

import structlog
from aiocache import RedisCache
from aiocache.serializers import PickleSerializer
from pydantic import BaseModel

from ..env import get_redis_cache_url

_cache: RedisCache | None = None
logger = structlog.get_logger()


def get_cache() -> RedisCache:
  """Initialize the Redis cache."""

  global _cache
  if _cache is not None:
    return _cache

  url_pattern = re.compile(r"redis://([^:]+):(\d+)/(\d+)")
  _match = url_pattern.match(get_redis_cache_url())
  if _match:
    host, port, db = _match.groups()
  else:
    raise ValueError("Invalid Redis cache URL")

  _cache = RedisCache(
    endpoint=host, port=int(port), db=int(db), serializer=PickleSerializer(), namespace="wakeup"
  )
  return _cache


class _CacheDecorator:
  def __init__(self, ttl: int | None = None):
    self.ttl = ttl

  def _process_arg(self, arg):
    """Recursively processes arguments, converting BaseModel instances to dicts."""
    if isinstance(arg, BaseModel):
      return arg.model_dump()
    elif isinstance(arg, (list, tuple)):
      return type(arg)(self._process_arg(item) for item in arg)
    elif isinstance(arg, dict):
      return {self._process_arg(k): self._process_arg(v) for k, v in arg.items()}
    return arg

  def _generate_cache_key(self, func, args, kwargs) -> bytes:
    """Generates a unique cache key based on function arguments."""
    processed_args = self._process_arg(args)
    processed_kwargs = cast(dict, self._process_arg(kwargs))

    # Sort kwargs to ensure consistent key generation regardless of argument order
    sorted_kwargs = tuple(sorted(processed_kwargs.items()))
    key_data = (func.__module__, func.__name__, processed_args, sorted_kwargs)
    return pickle.dumps(key_data)

  async def _get_from_cache(self, cache_instance: RedisCache, cache_key: bytes, func_name: str):
    """Attempts to retrieve a value from the cache."""
    cached_result = await cache_instance.get(cache_key)
    if cached_result is not None:
      logger.debug(f"Cache hit for {func_name}")
    return cached_result

  async def _set_to_cache(
    self, cache_instance: RedisCache, cache_key: bytes, result, func_name: str
  ) -> None:
    """Stores a value in the cache."""
    logger.debug(f"Cache miss for {func_name}")
    await cache_instance.set(cache_key, result, ttl=self.ttl)

  def __call__(self, func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
      _cache_instance = get_cache()
      cache_key = self._generate_cache_key(func, args, kwargs)

      cached_result = await self._get_from_cache(_cache_instance, cache_key, func.__name__)
      if cached_result is not None:
        return cached_result

      try:
        result = await func(*args, **kwargs)
      except Exception:
        logger.debug(f"Function {func.__name__} raised an exception, not caching.")
        raise

      await self._set_to_cache(_cache_instance, cache_key, result, func.__name__)
      return result

    return wrapper


cached = _CacheDecorator
