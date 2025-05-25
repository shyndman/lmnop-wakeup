from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.weather_lang import WeatherLang
from ...models.weather_response_200 import WeatherResponse200
from ...models.weather_response_400 import WeatherResponse400
from ...models.weather_response_404 import WeatherResponse404
from ...models.weather_response_500 import WeatherResponse500
from ...models.weather_response_502 import WeatherResponse502
from ...types import Response


def _get_kwargs(
  api_key: str,
  lat_and_long_or_time: str,
  *,
  exclude: None | str = None,
  extend: None | str = None,
  lang: None | WeatherLang = None,
  units: None | str = None,
  version: None | int = None,
  tmextra: None | int = None,
  icon: None | str = None,
) -> dict[str, Any]:
  params: dict[str, Any] = {}

  params["exclude"] = exclude

  params["extend"] = extend

  json_lang: None | str = None
  if lang is not None:
    json_lang = lang.value

  params["lang"] = json_lang

  params["units"] = units

  params["version"] = version

  params["tmextra"] = tmextra

  params["icon"] = icon

  params = {k: v for k, v in params.items() if v is not None and v is not None}

  _kwargs: dict[str, Any] = {
    "method": "get",
    "url": f"/forecast/{api_key}/{lat_and_long_or_time}",
    "params": params,
  }

  return _kwargs


def _parse_response(
  *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
  WeatherResponse200
  | WeatherResponse400
  | WeatherResponse404
  | WeatherResponse500
  | WeatherResponse502
  | str
  | None
):
  if response.status_code == 400:
    response_400 = WeatherResponse400.from_dict(response.json())

    return response_400
  if response.status_code == 401:
    response_401 = response.text
    return response_401
  if response.status_code == 404:
    response_404 = WeatherResponse404.from_dict(response.json())

    return response_404
  if response.status_code == 429:
    response_429 = response.text
    return response_429
  if response.status_code == 500:
    response_500 = WeatherResponse500.from_dict(response.json())

    return response_500
  if response.status_code == 502:
    response_502 = WeatherResponse502.from_dict(response.json())

    return response_502
  if response.status_code == 200:
    response_200 = WeatherResponse200.from_dict(response.json())

    return response_200
  if client.raise_on_unexpected_status:
    raise errors.UnexpectedStatus(response.status_code, response.content)
  else:
    return None


def _build_response(
  *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
  WeatherResponse200
  | WeatherResponse400
  | WeatherResponse404
  | WeatherResponse500
  | WeatherResponse502
  | str
]:
  return Response(
    status_code=HTTPStatus(response.status_code),
    content=response.content,
    headers=response.headers,
    parsed=_parse_response(client=client, response=response),
  )


def sync_detailed(
  api_key: str,
  lat_and_long_or_time: str,
  *,
  client: AuthenticatedClient | Client,
  exclude: None | str = None,
  extend: None | str = None,
  lang: None | WeatherLang = None,
  units: None | str = None,
  version: None | int = None,
  tmextra: None | int = None,
  icon: None | str = None,
) -> Response[
  WeatherResponse200
  | WeatherResponse400
  | WeatherResponse404
  | WeatherResponse500
  | WeatherResponse502
  | str
]:
  """Make a request to Pirate Weather

   Fetch a weather forecast or get historical weather data based on input latitude and longitude.

  Args:
      api_key (str):
      lat_and_long_or_time (str):
      exclude (None | str):
      extend (None | str):
      lang (None | WeatherLang):
      units (None | str):
      version (None | int):
      tmextra (None | int):
      icon (None | str):

  Raises:
      errors.UnexpectedStatus: If the server returns an undocumented status code and
          Client.raise_on_unexpected_status is True.
      httpx.TimeoutException: If the request takes longer than Client.timeout.

  Returns:
      Response[WeatherResponse200 | WeatherResponse400 | WeatherResponse404 | WeatherResponse500 |
      WeatherResponse502 | str]
  """

  kwargs = _get_kwargs(
    api_key=api_key,
    lat_and_long_or_time=lat_and_long_or_time,
    exclude=exclude,
    extend=extend,
    lang=lang,
    units=units,
    version=version,
    tmextra=tmextra,
    icon=icon,
  )

  response = client.get_httpx_client().request(
    **kwargs,
  )

  return _build_response(client=client, response=response)


def sync(
  api_key: str,
  lat_and_long_or_time: str,
  *,
  client: AuthenticatedClient | Client,
  exclude: None | str = None,
  extend: None | str = None,
  lang: None | WeatherLang = None,
  units: None | str = None,
  version: None | int = None,
  tmextra: None | int = None,
  icon: None | str = None,
) -> (
  WeatherResponse200
  | WeatherResponse400
  | WeatherResponse404
  | WeatherResponse500
  | WeatherResponse502
  | str
  | None
):
  """Make a request to Pirate Weather

   Fetch a weather forecast or get historical weather data based on input latitude and longitude.

  Args:
      api_key (str):
      lat_and_long_or_time (str):
      exclude (None | str):
      extend (None | str):
      lang (None | WeatherLang):
      units (None | str):
      version (None | int):
      tmextra (None | int):
      icon (None | str):

  Raises:
      errors.UnexpectedStatus: If the server returns an undocumented status code and
          Client.raise_on_unexpected_status is True.
      httpx.TimeoutException: If the request takes longer than Client.timeout.

  Returns:
      WeatherResponse200 | WeatherResponse400 | WeatherResponse404 | WeatherResponse500 |
      WeatherResponse502 | str | None
  """

  return sync_detailed(
    api_key=api_key,
    lat_and_long_or_time=lat_and_long_or_time,
    client=client,
    exclude=exclude,
    extend=extend,
    lang=lang,
    units=units,
    version=version,
    tmextra=tmextra,
    icon=icon,
  ).parsed


async def asyncio_detailed(
  api_key: str,
  lat_and_long_or_time: str,
  *,
  client: AuthenticatedClient | Client,
  exclude: None | str = None,
  extend: None | str = None,
  lang: None | WeatherLang = None,
  units: None | str = None,
  version: None | int = None,
  tmextra: None | int = None,
  icon: None | str = None,
) -> Response[
  WeatherResponse200
  | WeatherResponse400
  | WeatherResponse404
  | WeatherResponse500
  | WeatherResponse502
  | str
]:
  """Make a request to Pirate Weather

   Fetch a weather forecast or get historical weather data based on input latitude and longitude.

  Args:
      api_key (str):
      lat_and_long_or_time (str):
      exclude (None | str):
      extend (None | str):
      lang (None | WeatherLang):
      units (None | str):
      version (None | int):
      tmextra (None | int):
      icon (None | str):

  Raises:
      errors.UnexpectedStatus: If the server returns an undocumented status code and
          Client.raise_on_unexpected_status is True.
      httpx.TimeoutException: If the request takes longer than Client.timeout.

  Returns:
      Response[WeatherResponse200 | WeatherResponse400 | WeatherResponse404 | WeatherResponse500 |
      WeatherResponse502 | str]
  """

  kwargs = _get_kwargs(
    api_key=api_key,
    lat_and_long_or_time=lat_and_long_or_time,
    exclude=exclude,
    extend=extend,
    lang=lang,
    units=units,
    version=version,
    tmextra=tmextra,
    icon=icon,
  )

  response = await client.get_async_httpx_client().request(**kwargs)

  return _build_response(client=client, response=response)


async def asyncio(
  api_key: str,
  lat_and_long_or_time: str,
  *,
  client: AuthenticatedClient | Client,
  exclude: None | str = None,
  extend: None | str = None,
  lang: None | WeatherLang = None,
  units: None | str = None,
  version: None | int = None,
  tmextra: None | int = None,
  icon: None | str = None,
) -> (
  WeatherResponse200
  | WeatherResponse400
  | WeatherResponse404
  | WeatherResponse500
  | WeatherResponse502
  | str
  | None
):
  """Make a request to Pirate Weather

   Fetch a weather forecast or get historical weather data based on input latitude and longitude.

  Args:
      api_key (str):
      lat_and_long_or_time (str):
      exclude (None | str):
      extend (None | str):
      lang (None | WeatherLang):
      units (None | str):
      version (None | int):
      tmextra (None | int):
      icon (None | str):

  Raises:
      errors.UnexpectedStatus: If the server returns an undocumented status code and
          Client.raise_on_unexpected_status is True.
      httpx.TimeoutException: If the request takes longer than Client.timeout.

  Returns:
      WeatherResponse200 | WeatherResponse400 | WeatherResponse404 | WeatherResponse500 |
      WeatherResponse502 | str | None
  """

  return (
    await asyncio_detailed(
      api_key=api_key,
      lat_and_long_or_time=lat_and_long_or_time,
      client=client,
      exclude=exclude,
      extend=extend,
      lang=lang,
      units=units,
      version=version,
      tmextra=tmextra,
      icon=icon,
    )
  ).parsed
