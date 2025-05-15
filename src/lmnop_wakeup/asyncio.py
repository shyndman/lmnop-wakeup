import asyncio
from collections.abc import Coroutine, Mapping
from typing import Any, TypeVar

K = TypeVar("K")  # Type for keys
T = TypeVar("T")  # Type for values


async def gather_map(coro_dict: Mapping[K, Coroutine[Any, Any, T]]) -> dict[K, T]:
  """
  Wait for a mapping of coroutines to complete and return their results
  with the same keys.

  Args:
      coro_dict: A mapping from keys of type K to coroutines that resolve to type T

  Returns:
      A dictionary with the same keys, but values are the results of the coroutines

  Example:
      async def fetch_data(url):
          # Some async operation
          return response

      urls = {
          "api1": fetch_data("https://api1.example.com"),
          "api2": fetch_data("https://api2.example.com")
      }

      # With string keys
      results = await wait_for_coroutines(urls)
      # results will be like: {"api1": response1, "api2": response2}

      # Or with any other hashable type as keys
      numeric_tasks = {
          1: some_async_task(),
          2: another_async_task()
      }
      numeric_results = await wait_for_coroutines(numeric_tasks)
  """
  # Create tasks from coroutines while preserving keys
  tasks = {key: asyncio.create_task(coro) for key, coro in coro_dict.items()}

  # Wait for all tasks to complete
  await asyncio.gather(*tasks.values())

  # Get results while preserving the original keys
  results = {key: task.result() for key, task in tasks.items()}

  return results
