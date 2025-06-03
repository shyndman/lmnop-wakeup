# Music Assistant Announcement Client Specification

## Overview

This document specifies the design and implementation of a robust Music Assistant announcement client that handles real-world scenarios including network failures, player unavailability, and provides comprehensive monitoring capabilities.

## Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                   AnnouncementClient                        │
├─────────────────────────────────────────────────────────────┤
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│ │ ConnectionMgr   │ │ PlayerDiscovery │ │ AudioValidator  │ │
│ │                 │ │                 │ │                 │ │
│ │ - Auto-reconnect│ │ - Capability    │ │ - Duration      │ │
│ │ - Health checks │ │   filtering     │ │   detection     │ │
│ │ - State mgmt    │ │ - Availability  │ │ - Format check  │ │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘ │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│ │ ErrorHandler    │ │ StateMonitor    │ │ AnnounceMgr     │ │
│ │                 │ │                 │ │                 │ │
│ │ - Retry logic   │ │ - Player events │ │ - Queue mgmt    │ │
│ │ - Fallbacks     │ │ - Progress      │ │ - Execution     │ │
│ │ - Logging       │ │ - Completion    │ │ - Callbacks     │ │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Feature Specifications

### 1. Error Handling

#### 1.1 Network Error Handling

**Objective**: Gracefully handle network connectivity issues, timeouts, and protocol errors.

**Implementation Requirements**:

```python
from enum import Enum
from dataclasses import dataclass
from typing import Callable, Any
import asyncio
import logging

class ErrorType(Enum):
  NETWORK_TIMEOUT = "network_timeout"
  CONNECTION_REFUSED = "connection_refused"
  PLAYER_UNAVAILABLE = "player_unavailable"
  INVALID_URL = "invalid_url"
  AUDIO_FORMAT_UNSUPPORTED = "audio_format_unsupported"
  ANNOUNCEMENT_FAILED = "announcement_failed"
  SERVER_ERROR = "server_error"

@dataclass
class ErrorContext:
  error_type: ErrorType
  original_exception: Exception | None
  player_id: str | None
  url: str | None
  attempt_count: int
  timestamp: float
  details: dict[str, Any]

class ErrorHandler:
  def __init__(self,
               max_retries: int = 3,
               retry_delays: list[float] = [1.0, 2.0, 5.0],
               error_callback: Callable[[ErrorContext], None] | None = None):
    self.max_retries = max_retries
    self.retry_delays = retry_delays
    self.error_callback = error_callback
    self.logger = logging.getLogger(__name__)

  async def with_retry(self,
                       operation: Callable[[], Any],
                       error_types: list[ErrorType],
                       context: dict[str, Any] | None = None) -> Any:
    """Execute operation with automatic retry logic."""
    for attempt in range(self.max_retries + 1):
      try:
        return await operation()
      except Exception as e:
        error_type = self._classify_error(e)
        error_context = ErrorContext(
          error_type=error_type,
          original_exception=e,
          player_id=context.get("player_id") if context else None,
          url=context.get("url") if context else None,
          attempt_count=attempt + 1,
          timestamp=time.time(),
          details=context or {}
        )

        if error_type not in error_types or attempt >= self.max_retries:
          self._handle_final_error(error_context)
          raise

        delay = self.retry_delays[min(attempt, len(self.retry_delays) - 1)]
        self.logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
        await asyncio.sleep(delay)

  def _classify_error(self, exception: Exception) -> ErrorType:
    """Map exceptions to error types for appropriate handling."""
    # Implementation details for mapping different exception types
    pass
```

#### 1.2 Player Availability Validation

```python
async def validate_player_available(self, player_id: str) -> bool:
  """Verify player is available and responsive before attempting announcements."""
  try:
    player = self.client.players.get(player_id)
    if not player:
      raise PlayerError(f"Player {player_id} not found")

    if not player.available:
      raise PlayerError(f"Player {player.name} is not available")

    if not player.powered:
      self.logger.warning(f"Player {player.name} is powered off - attempting to power on")
      await self.client.players.player_command_power(player_id, powered=True)
      # Wait for power state change
      await self._wait_for_player_state(player_id, "powered", True, timeout=10.0)

    return True

  except Exception as e:
    self.logger.error(f"Player validation failed for {player_id}: {e}")
    return False
```

#### 1.3 URL Validation

```python
import aiohttp
from urllib.parse import urlparse

async def validate_audio_url(self, url: str) -> tuple[bool, dict[str, Any]]:
  """Validate audio URL accessibility and gather metadata."""
  try:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
      return False, {"error": "Invalid URL format"}

    async with aiohttp.ClientSession() as session:
      async with session.head(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
        if response.status >= 400:
          return False, {"error": f"HTTP {response.status}", "status": response.status}

        content_type = response.headers.get('content-type', '').lower()
        content_length = response.headers.get('content-length')

        # Validate audio content type
        supported_types = ['audio/', 'application/ogg']
        if not any(content_type.startswith(t) for t in supported_types):
          return False, {"error": f"Unsupported content type: {content_type}"}

        metadata = {
          "content_type": content_type,
          "content_length": int(content_length) if content_length else None,
          "accessible": True
        }

        return True, metadata

  except Exception as e:
    return False, {"error": str(e), "exception_type": type(e).__name__}
```

### 2. Connection State Management

#### 2.1 Connection Health Monitoring

```python
class ConnectionState(Enum):
  DISCONNECTED = "disconnected"
  CONNECTING = "connecting"
  CONNECTED = "connected"
  RECONNECTING = "reconnecting"
  FAILED = "failed"

class ConnectionManager:
  def __init__(self,
               server_url: str,
               health_check_interval: float = 30.0,
               reconnect_delay: float = 5.0,
               max_reconnect_attempts: int = 10):
    self.server_url = server_url
    self.health_check_interval = health_check_interval
    self.reconnect_delay = reconnect_delay
    self.max_reconnect_attempts = max_reconnect_attempts
    self.state = ConnectionState.DISCONNECTED
    self.client: MusicAssistantClient | None = None
    self.session: aiohttp.ClientSession | None = None
    self.health_check_task: asyncio.Task | None = None
    self.reconnect_attempts = 0
    self.state_callbacks: list[Callable[[ConnectionState], None]] = []

  async def connect(self) -> bool:
    """Establish initial connection with full state management."""
    if self.state in [ConnectionState.CONNECTED, ConnectionState.CONNECTING]:
      return True

    self._set_state(ConnectionState.CONNECTING)

    try:
      self.session = aiohttp.ClientSession()
      self.client = MusicAssistantClient(self.server_url, self.session)

      # Connect with timeout
      await asyncio.wait_for(self.client.connect(), timeout=10.0)

      # Start listening for events
      init_ready = asyncio.Event()
      self.listen_task = asyncio.create_task(self.client.start_listening(init_ready))
      await asyncio.wait_for(init_ready.wait(), timeout=15.0)

      self._set_state(ConnectionState.CONNECTED)
      self.reconnect_attempts = 0

      # Start health monitoring
      self.health_check_task = asyncio.create_task(self._health_check_loop())

      return True

    except Exception as e:
      self.logger.error(f"Connection failed: {e}")
      await self._cleanup_connection()
      self._set_state(ConnectionState.FAILED)
      return False

  async def _health_check_loop(self):
    """Continuously monitor connection health."""
    while self.state == ConnectionState.CONNECTED:
      try:
        await asyncio.sleep(self.health_check_interval)

        if not self.client or not self.client.connection.connected:
          self.logger.warning("Connection lost - initiating reconnect")
          await self._initiate_reconnect()
          break

        # Perform lightweight health check
        try:
          await asyncio.wait_for(
            self.client.send_command("ping"),
            timeout=5.0
          )
        except asyncio.TimeoutError:
          self.logger.warning("Health check timeout - connection may be stale")
          await self._initiate_reconnect()
          break

      except asyncio.CancelledError:
        break
      except Exception as e:
        self.logger.error(f"Health check error: {e}")
        await self._initiate_reconnect()
        break

  async def _initiate_reconnect(self):
    """Handle connection loss and attempt reconnection."""
    if self.state == ConnectionState.RECONNECTING:
      return  # Already reconnecting

    self._set_state(ConnectionState.RECONNECTING)
    await self._cleanup_connection()

    while (self.reconnect_attempts < self.max_reconnect_attempts and
           self.state == ConnectionState.RECONNECTING):

      self.reconnect_attempts += 1
      self.logger.info(f"Reconnection attempt {self.reconnect_attempts}/{self.max_reconnect_attempts}")

      await asyncio.sleep(self.reconnect_delay)

      if await self.connect():
        self.logger.info("Reconnection successful")
        return

      # Exponential backoff
      self.reconnect_delay = min(self.reconnect_delay * 1.5, 60.0)

    self.logger.error("Max reconnection attempts reached")
    self._set_state(ConnectionState.FAILED)
```

### 3. Player State Monitoring

#### 3.1 Real-time State Tracking

```python
@dataclass
class PlayerStateSnapshot:
  player_id: str
  timestamp: float
  state: PlayerState
  volume_level: int | None
  volume_muted: bool | None
  powered: bool | None
  announcement_in_progress: bool
  current_media: PlayerMedia | None

class PlayerStateMonitor:
  def __init__(self, client: MusicAssistantClient):
    self.client = client
    self.state_history: dict[str, list[PlayerStateSnapshot]] = {}
    self.state_callbacks: dict[str, list[Callable[[PlayerStateSnapshot], None]]] = {}
    self.announcement_callbacks: dict[str, list[Callable[[str, bool], None]]] = {}

    # Subscribe to player events
    self.client.subscribe(
      self._handle_player_event,
      event_filter=(EventType.PLAYER_UPDATED,)
    )

  def track_player(self, player_id: str,
                   state_callback: Callable[[PlayerStateSnapshot], None] | None = None,
                   announcement_callback: Callable[[str, bool], None] | None = None):
    """Start tracking a specific player's state changes."""
    if player_id not in self.state_history:
      self.state_history[player_id] = []
      self.state_callbacks[player_id] = []
      self.announcement_callbacks[player_id] = []

    if state_callback:
      self.state_callbacks[player_id].append(state_callback)

    if announcement_callback:
      self.announcement_callbacks[player_id].append(announcement_callback)

    # Take initial snapshot
    if player := self.client.players.get(player_id):
      self._record_state(player)

  def _handle_player_event(self, event: MassEvent):
    """Process incoming player state changes."""
    if event.event == EventType.PLAYER_UPDATED and event.object_id:
      player = Player.from_dict(event.data)
      self._record_state(player)

  def _record_state(self, player: Player):
    """Record a state snapshot and trigger callbacks."""
    snapshot = PlayerStateSnapshot(
      player_id=player.player_id,
      timestamp=time.time(),
      state=player.state,
      volume_level=player.volume_level,
      volume_muted=player.volume_muted,
      powered=player.powered,
      announcement_in_progress=player.announcement_in_progress,
      current_media=player.current_media
    )

    # Store in history (keep last 100 snapshots)
    history = self.state_history.get(player.player_id, [])
    history.append(snapshot)
    if len(history) > 100:
      history.pop(0)
    self.state_history[player.player_id] = history

    # Trigger state callbacks
    for callback in self.state_callbacks.get(player.player_id, []):
      try:
        callback(snapshot)
      except Exception as e:
        self.logger.error(f"State callback error: {e}")

    # Check for announcement state changes
    prev_snapshot = history[-2] if len(history) >= 2 else None
    if (prev_snapshot and
        prev_snapshot.announcement_in_progress != snapshot.announcement_in_progress):

      for callback in self.announcement_callbacks.get(player.player_id, []):
        try:
          callback(player.player_id, snapshot.announcement_in_progress)
        except Exception as e:
          self.logger.error(f"Announcement callback error: {e}")

  async def wait_for_announcement_completion(self,
                                           player_id: str,
                                           timeout: float = 60.0) -> bool:
    """Wait for an announcement to complete on the specified player."""
    start_time = time.time()

    while time.time() - start_time < timeout:
      player = self.client.players.get(player_id)
      if not player or not player.announcement_in_progress:
        return True
      await asyncio.sleep(0.5)

    return False
```

### 4. Player Discovery

#### 4.1 Capability-Based Filtering

```python
class PlayerCapability(Enum):
  PLAY_ANNOUNCEMENTS = "play_announcements"
  VOLUME_CONTROL = "volume_control"
  POWER_CONTROL = "power_control"
  CURRENTLY_AVAILABLE = "currently_available"

class PlayerDiscovery:
  def __init__(self, client: MusicAssistantClient):
    self.client = client
    self.capability_cache: dict[str, set[PlayerCapability]] = {}
    self.last_discovery = 0.0
    self.cache_ttl = 30.0  # 30 seconds

  async def discover_players(self,
                           required_capabilities: list[PlayerCapability] | None = None,
                           refresh_cache: bool = False) -> list[Player]:
    """Discover players matching capability requirements."""
    if refresh_cache or time.time() - self.last_discovery > self.cache_ttl:
      await self._refresh_capabilities()

    if not required_capabilities:
      required_capabilities = [PlayerCapability.CURRENTLY_AVAILABLE]

    matching_players = []

    for player in self.client.players.players:
      player_caps = self.capability_cache.get(player.player_id, set())

      if all(cap in player_caps for cap in required_capabilities):
        matching_players.append(player)

    return matching_players

  async def _refresh_capabilities(self):
    """Refresh capability cache for all players."""
    self.capability_cache.clear()

    for player in self.client.players.players:
      capabilities = set()

      # Check availability
      if player.available and player.powered is not False:
        capabilities.add(PlayerCapability.CURRENTLY_AVAILABLE)

      # Check announcement support (most players support this)
      if PlayerFeature.PLAY_ANNOUNCEMENT in player.supported_features:
        capabilities.add(PlayerCapability.PLAY_ANNOUNCEMENTS)

      # Check volume control
      if (player.volume_level is not None and
          PlayerFeature.VOLUME_SET in player.supported_features):
        capabilities.add(PlayerCapability.VOLUME_CONTROL)

      # Check power control
      if (player.powered is not None and
          PlayerFeature.POWER in player.supported_features):
        capabilities.add(PlayerCapability.POWER_CONTROL)

      self.capability_cache[player.player_id] = capabilities

    self.last_discovery = time.time()

  def get_announcement_capable_players(self) -> list[Player]:
    """Convenience method to get players that can handle announcements."""
    return asyncio.run(self.discover_players([
      PlayerCapability.CURRENTLY_AVAILABLE,
      PlayerCapability.PLAY_ANNOUNCEMENTS
    ]))
```

### 5. Audio Duration Detection

#### 5.1 Pre-announcement Analysis

```python
import subprocess
import json
from pathlib import Path

class AudioAnalyzer:
  def __init__(self):
    self.duration_cache: dict[str, float] = {}
    self.cache_file = Path("audio_duration_cache.json")
    self._load_cache()

  async def get_audio_duration(self, url: str) -> float | None:
    """Get audio duration in seconds, with caching."""
    if url in self.duration_cache:
      return self.duration_cache[url]

    duration = await self._analyze_audio_duration(url)

    if duration is not None:
      self.duration_cache[url] = duration
      self._save_cache()

    return duration

  async def _analyze_audio_duration(self, url: str) -> float | None:
    """Analyze audio duration using multiple methods."""

    # Method 1: Try HTTP Content-Length + bitrate estimation
    duration = await self._estimate_from_headers(url)
    if duration:
      return duration

    # Method 2: Use ffprobe if available
    duration = await self._ffprobe_duration(url)
    if duration:
      return duration

    # Method 3: Partial download and analysis
    duration = await self._partial_download_analysis(url)
    return duration

  async def _estimate_from_headers(self, url: str) -> float | None:
    """Estimate duration from HTTP headers."""
    try:
      async with aiohttp.ClientSession() as session:
        async with session.head(url) as response:
          content_length = response.headers.get('content-length')
          content_type = response.headers.get('content-type', '').lower()

          if not content_length:
            return None

          size_bytes = int(content_length)

          # Rough bitrate estimates for common formats
          bitrate_estimates = {
            'audio/mpeg': 128000,  # 128 kbps MP3
            'audio/wav': 1411200,  # 16-bit 44.1kHz stereo WAV
            'audio/aac': 128000,   # 128 kbps AAC
            'audio/ogg': 112000,   # 112 kbps OGG
          }

          for content_prefix, bitrate in bitrate_estimates.items():
            if content_type.startswith(content_prefix):
              duration_seconds = (size_bytes * 8) / bitrate
              return duration_seconds

          return None

    except Exception as e:
      self.logger.debug(f"Header analysis failed for {url}: {e}")
      return None

  async def _ffprobe_duration(self, url: str) -> float | None:
    """Use ffprobe to get exact duration."""
    try:
      cmd = [
        'ffprobe', '-v', 'quiet', '-print_format', 'json',
        '-show_format', url
      ]

      proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
      )

      stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10.0)

      if proc.returncode == 0:
        data = json.loads(stdout.decode())
        duration = float(data['format']['duration'])
        return duration

      return None

    except (FileNotFoundError, asyncio.TimeoutError, json.JSONDecodeError, KeyError):
      return None
    except Exception as e:
      self.logger.debug(f"ffprobe analysis failed for {url}: {e}")
      return None

  async def _partial_download_analysis(self, url: str) -> float | None:
    """Download first chunk and analyze for duration markers."""
    try:
      async with aiohttp.ClientSession() as session:
        headers = {'Range': 'bytes=0-8192'}  # First 8KB
        async with session.get(url, headers=headers) as response:
          if response.status in [200, 206]:  # OK or Partial Content
            chunk = await response.read()

            # Basic MP3 header analysis
            if chunk.startswith(b'ID3') or (len(chunk) > 3 and chunk[0:3] == b'\xff\xfb'):
              return self._analyze_mp3_chunk(chunk)

            # WAV header analysis
            if chunk.startswith(b'RIFF') and b'WAVE' in chunk[:12]:
              return self._analyze_wav_chunk(chunk)

      return None

    except Exception as e:
      self.logger.debug(f"Partial download analysis failed for {url}: {e}")
      return None

  def _save_cache(self):
    """Save duration cache to disk."""
    try:
      with open(self.cache_file, 'w') as f:
        json.dump(self.duration_cache, f)
    except Exception as e:
      self.logger.debug(f"Cache save failed: {e}")

  def _load_cache(self):
    """Load duration cache from disk."""
    try:
      if self.cache_file.exists():
        with open(self.cache_file, 'r') as f:
          self.duration_cache = json.load(f)
    except Exception as e:
      self.logger.debug(f"Cache load failed: {e}")
      self.duration_cache = {}
```

## Integration Pattern

### Complete Announcement Client

```python
class AnnouncementClient:
  def __init__(self, server_url: str, **kwargs):
    self.connection_mgr = ConnectionManager(server_url, **kwargs)
    self.error_handler = ErrorHandler()
    self.state_monitor: PlayerStateMonitor | None = None
    self.player_discovery: PlayerDiscovery | None = None
    self.audio_analyzer = AudioAnalyzer()
    self.logger = logging.getLogger(__name__)

  async def connect(self) -> bool:
    """Connect and initialize all components."""
    if not await self.connection_mgr.connect():
      return False

    self.state_monitor = PlayerStateMonitor(self.connection_mgr.client)
    self.player_discovery = PlayerDiscovery(self.connection_mgr.client)

    return True

  async def play_announcement(self,
                            player_id: str,
                            url: str,
                            volume_level: int | None = None,
                            wait_for_completion: bool = True,
                            timeout: float = 60.0) -> bool:
    """Play announcement with full error handling and monitoring."""

    # Pre-flight checks
    context = {"player_id": player_id, "url": url}

    # Validate URL
    url_valid, url_info = await self.error_handler.with_retry(
      lambda: self.audio_analyzer.validate_audio_url(url),
      [ErrorType.NETWORK_TIMEOUT],
      context
    )

    if not url_valid:
      raise AnnouncementError(f"Invalid URL: {url_info}")

    # Validate player
    await self.error_handler.with_retry(
      lambda: self._validate_player_available(player_id),
      [ErrorType.NETWORK_TIMEOUT],
      context
    )

    # Get duration for timeout calculation
    duration = await self.audio_analyzer.get_audio_duration(url)
    if duration and timeout == 60.0:  # Use dynamic timeout
      timeout = max(duration + 10.0, 30.0)

    # Start monitoring
    if wait_for_completion:
      self.state_monitor.track_player(player_id)

    # Execute announcement
    await self.error_handler.with_retry(
      lambda: self.connection_mgr.client.players.play_announcement(
        player_id=player_id,
        url=url,
        volume_level=volume_level
      ),
      [ErrorType.NETWORK_TIMEOUT, ErrorType.SERVER_ERROR],
      context
    )

    # Wait for completion if requested
    if wait_for_completion:
      return await self.state_monitor.wait_for_announcement_completion(
        player_id, timeout
      )

    return True

  async def discover_announcement_players(self) -> list[Player]:
    """Find all players capable of announcements."""
    return await self.player_discovery.discover_players([
      PlayerCapability.CURRENTLY_AVAILABLE,
      PlayerCapability.PLAY_ANNOUNCEMENTS
    ])
```

## Usage Examples

### Basic Usage

```python
async def main():
  client = AnnouncementClient("http://music.don:8095/")

  if not await client.connect():
    print("Failed to connect")
    return

  # Discover available players
  players = await client.discover_announcement_players()
  print(f"Found {len(players)} announcement-capable players")

  # Play announcement
  if players:
    success = await client.play_announcement(
      players[0].player_id,
      "http://192.168.86.208:9315/file/scott-time-for-bed.mp3",
      volume_level=70
    )
    print(f"Announcement {'succeeded' if success else 'failed'}")

asyncio.run(main())
```

### Advanced Usage with Monitoring

```python
async def announcement_with_monitoring():
  client = AnnouncementClient("http://music.don:8095/")
  await client.connect()

  # Set up state monitoring
  def on_state_change(snapshot: PlayerStateSnapshot):
    print(f"Player {snapshot.player_id} state: {snapshot.state}")

  def on_announcement_change(player_id: str, in_progress: bool):
    status = "started" if in_progress else "completed"
    print(f"Announcement {status} on {player_id}")

  players = await client.discover_announcement_players()
  if players:
    player_id = players[0].player_id

    client.state_monitor.track_player(
      player_id,
      state_callback=on_state_change,
      announcement_callback=on_announcement_change
    )

    await client.play_announcement(
      player_id,
      "http://192.168.86.208:9315/file/weather-spooky-storm.wav"
    )
```

This specification provides comprehensive implementation guidance for a robust Music Assistant announcement client that handles real-world scenarios and provides excellent monitoring capabilities.
