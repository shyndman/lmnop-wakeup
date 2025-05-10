# Pirate Weather API Client

This directory contains a Python client for interacting with the Pirate Weather API. It allows you to easily fetch weather forecasts and historical data.

## Installation

(This client is typically used as part of a larger project. If it were a standalone package, you might install it via pip. For now, assume it's available within your project structure.)

## Usage

### 1. Importing Necessary Components

```python
from pirate_weather_api_client import Client
from pirate_weather_api_client.api.weather import weather
from pirate_weather_api_client.models import WeatherResponse200 # Example model for successful response
from pirate_weather_api_client.types import Response # For detailed responses with status, headers, etc.
from pirate_weather_api_client.errors import UnexpectedStatus # For error handling
```

### 2. Initializing the Client

The client requires a `base_url`. For the official Pirate Weather API, this is `https://api.pirateweather.net`.

```python
BASE_URL = "https://api.pirateweather.net"
# Initialize the client
# You can also pass other httpx client arguments like timeout, headers, etc.
# client = Client(base_url=BASE_URL, timeout=10.0)
client = Client(base_url=BASE_URL)
```

### 3. Making API Calls

The primary functions for fetching weather data are located in the `pirate_weather_api_client.api.weather.weather` module. You will need your Pirate Weather API key for these calls.

The main endpoint allows you to fetch current weather, minutely, hourly, and daily forecasts, as well as historical data.

#### Synchronous Call

To make a synchronous API call:

```python
API_KEY = "YOUR_PIRATE_WEATHER_API_KEY"
# Latitude, Longitude for current/forecasted weather
LAT_LONG = "37.8267,-122.4233"
# For historical data, append time: "LAT,LONG,YYYY-MM-DDTHH:MM:SS"
# e.g., "37.8267,-122.4233,2023-07-15T12:00:00"

try:
    # Using the simple 'sync' function for parsed data or None
    weather_data: WeatherResponse200 | None = weather.sync(
        api_key=API_KEY,
        lat_and_long_or_time=LAT_LONG,
        client=client,
        # Optional parameters:
        # units="si",  # e.g., "auto", "ca", "uk2", "us", "si"
        # exclude="minutely,hourly", # Comma-separated list of blocks to exclude
        # lang="es" # Language for summaries
    )

    if weather_data and weather_data.currently:
        print(f"Current Temperature: {weather_data.currently.temperature} degrees")
        print(f"Summary: {weather_data.currently.summary}")
    elif weather_data:
        print("Weather data received, but 'currently' block might be missing or empty.")
    else:
        print("Failed to retrieve weather data (check API key, network, or if the response was non-200 and not an error model).")

    # Using 'sync_detailed' for the full response object
    # This is useful if you need to check status codes, headers, or handle different error models
    detailed_response: Response[WeatherResponse200 | None] = weather.sync_detailed(
        api_key=API_KEY,
        lat_and_long_or_time=LAT_LONG,
        client=client
    )
    print(f"Status Code: {detailed_response.status_code}")
    if detailed_response.parsed and isinstance(detailed_response.parsed, WeatherResponse200):
        if detailed_response.parsed.currently:
            print(f"Parsed Temperature (from detailed): {detailed_response.parsed.currently.temperature}")
    else:
        # Handle cases where parsing failed or a different error model was returned
        print(f"Failed to parse or non-200 response. Raw content: {detailed_response.content[:200]}...")


except UnexpectedStatus as e:
    print(f"API returned an unexpected status: {e.status_code}, Content: {e.content}")
except Exception as e:
    print(f"An error occurred: {e}")
finally:
    # Close the client if you're done with it (important if not using a context manager)
    client.get_httpx_client().close()
```

#### Asynchronous Call

To make an asynchronous API call, you can use the `asyncio` functions and manage the client lifecycle with `async with`.

```python
import asyncio

async def fetch_weather_async():
    BASE_URL = "https://api.pirateweather.net"
    API_KEY = "YOUR_PIRATE_WEATHER_API_KEY"
    LAT_LONG = "37.8267,-122.4233"

    async with Client(base_url=BASE_URL) as async_client: # Client used as an async context manager
        try:
            # Using 'asyncio' for parsed data or None
            weather_data: WeatherResponse200 | None = await weather.asyncio(
                api_key=API_KEY,
                lat_and_long_or_time=LAT_LONG,
                client=async_client,
                # units="si"
            )

            if weather_data and weather_data.currently:
                print(f"Async Current Temperature: {weather_data.currently.temperature}")
            else:
                print("Async: Failed to retrieve weather data or 'currently' block missing.")

            # Using 'asyncio_detailed' for the full response object
            detailed_response_async: Response[WeatherResponse200 | None] = await weather.asyncio_detailed(
                api_key=API_KEY,
                lat_and_long_or_time=LAT_LONG,
                client=async_client
            )
            print(f"Async Status Code: {detailed_response_async.status_code}")
            if detailed_response_async.parsed and isinstance(detailed_response_async.parsed, WeatherResponse200):
                 if detailed_response_async.parsed.currently:
                    print(f"Parsed Async Temperature (from detailed): {detailed_response_async.parsed.currently.temperature}")
            else:
                print(f"Async: Failed to parse or non-200 response. Raw content: {detailed_response_async.content[:200]}...")


        except UnexpectedStatus as e:
            print(f"Async API returned an unexpected status: {e.status_code}, Content: {e.content}")
        except Exception as e:
            print(f"An async error occurred: {e}")

# To run the async function:
# if __name__ == "__main__":
# asyncio.run(fetch_weather_async())
```

### 4. API Parameters

The weather API functions (`sync`, `sync_detailed`, `asyncio`, `asyncio_detailed`) accept several optional keyword parameters to customize the request:

- `exclude` (`str` | `Unset`): Comma-separated list of data blocks to exclude (e.g., `"minutely,hourly"`).
- `extend` (`str` | `Unset`): Set to `"hourly"` to extend the hourly forecast from 48 hours to 168 hours.
- `lang` (`WeatherLang` | `Unset`): Language for text summaries and alerts. Import `WeatherLang` from `pirate_weather_api_client.models`.
- `units` (`str` | `Unset`): Units for the forecast. Options include:
    - `"auto"`: Selects units automatically based on geographic location.
    - `"ca"`: SI units, but with windSpeed in kilometers per hour.
    - `"uk2"`: SI units, but with windSpeed in miles per hour and visibility in miles.
    - `"us"`: Imperial units.
    - `"si"`: SI units (default).
- `version` (`int` | `Unset`): API version.
- `tmextra` (`int` | `Unset`): Include extra time machine data.
- `icon` (`str` | `Unset`): Icon set to use.

For detailed information on these parameters, refer to the official Pirate Weather API documentation.

### 5. Response Models

API responses are parsed into `attrs`-based models, which are defined in the `pirate_weather_api_client.models` directory.
- A successful call to the weather endpoint typically returns `WeatherResponse200`.
- Error responses (e.g., 400, 404, 500) are also parsed into specific models like `WeatherResponse400`, etc. The `sync_detailed` and `asyncio_detailed` methods are useful for inspecting the status code and handling these different response types.

### 6. Error Handling

- `errors.UnexpectedStatus`: Raised if the client is initialized with `raise_on_unexpected_status=True` (default is `False`) and the API returns an undocumented HTTP status code.
- Standard `httpx` exceptions (e.g., `httpx.TimeoutException`, `httpx.ConnectError`) can also occur.

## Client Structure

- **`client.py`**: Defines `Client` for making API requests. (The `AuthenticatedClient` is also available but less relevant for Pirate Weather's API key usage model).
- **`api/`**: Contains modules for specific API endpoints. Currently, `api/weather/weather.py` holds the weather forecast functions.
- **`models/`**: Includes all data models for request and response payloads (e.g., `WeatherResponse200`, `Currently`, `DailyDataItem`).
- **`types.py`**: Defines shared utility types like `Response`, `File`, and `UNSET`.
- **`errors.py`**: Contains custom exception classes like `UnexpectedStatus`.

## Further Information

For more details on API parameters, response fields, and data models, consult the official Pirate Weather API documentation and explore the generated model files in this client library.
