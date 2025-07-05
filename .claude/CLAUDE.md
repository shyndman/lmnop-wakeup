# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

**Setup and Dependencies:**
```bash
# Install dependencies (must have uv installed)
uv add .
uv add --dev .

# Build project
uv build
```

**Required Services:**
- PostgreSQL (for workflow checkpointing)
- Redis (for caching, optional but recommended)

**Key Python Dependencies:**
- `pydub-ng` - Audio file manipulation and concatenation
- `eyeD3` - ID3 tag management for MP3 files
- `langgraph` - Workflow orchestration
- `pydantic-ai` - AI agent framework
- `google-genai` - Gemini AI integration

**Code Quality:**
```bash
# Format and lint code
./scripts/fmt.sh
# Or manually:
uv tool run ruff check --fix
uv tool run ruff format

# Type checking is configured via pyproject.toml with pyright

# Test imports and code
uv run python -c "from lmnop_wakeup.env import get_final_out_path; print('Import successful')"
```

**Testing:**
```bash
# Run tests (must use opr for environment variables)
uv run pytest tests/

# Run specific test
uv run pytest tests/test_weather_api.py
```

**Running the Application:**
```bash
# Generate daily briefing script (primary use case)
op run --env-file=.env wakeup --briefing-date 2025-06-10 --current-location home

# Resume an interrupted workflow
op run --env-file=.env wakeup --briefing-date 2025-06-10 --thread-id <thread-id>

# Generate voiceover from existing script (obsolete - TTS now in main workflow)
op run --env-file=.env wakeup voiceover --briefing-date 2025-06-10

# Load external data
op run --env-file=.env wakeup load-data

# Run server mode
op run --env-file=.env wakeup server

# Test weather integration
op run --env-file=.env wakeup weather

# View available characters
op run --env-file=.env wakeup characters

# Announce briefing on Music Assistant
op run --env-file=.env wakeup announce --briefing-date 2025-06-10
```

**Important:** All `wakeup` commands MUST be run with `op run` (1Password CLI) to load required API keys from 1Password vault.

**Output Directory Structure:**
```
{DATA_PATH or user_state_path}/
└── 2025-06-10/                    # Date-based directory
    ├── brief.json                 # BriefingScript model
    ├── consolidated_brief.json    # ConsolidatedBriefingScript model
    ├── workflow_state.json        # Full workflow state dump
    ├── cost_report.json          # Cost tracking data
    ├── 0.wav, 1.wav, ...         # Individual TTS segments
    ├── briefing.mp3              # Combined audio (with ID3 tags)
    └── master_briefing.mp3       # Final audio with bells (with ID3 tags)
```

## Directory Structure & Responsibilities

```
src/lmnop_wakeup/
├── audio/                      # Audio generation and processing
│   ├── master.py              # Combines WAV files into MP3
│   ├── production.py          # Adds bells and production elements
│   ├── workflow.py            # TTS workflow subgraph
│   ├── id3_tags.py           # ID3 metadata tagging
│   ├── announcer.py          # Music Assistant integration
│   └── cover.png             # Podcast cover art
├── brief/                     # Script generation
│   ├── model.py              # BriefingScript, ConsolidatedBriefingScript models
│   ├── actors.py             # Character definitions (CHARACTER_POOL)
│   ├── script_writer_agent.py # Main script generation agent
│   └── content_optimizer.py  # Pre-script content analysis
├── core/                      # Shared utilities
│   ├── date.py               # Date/time helpers, get_ordinal_suffix()
│   ├── cache.py              # Caching decorators
│   ├── cost_tracking.py      # API cost tracking
│   └── tracing.py            # Observability helpers
├── events/                    # Calendar event handling
│   ├── model.py              # CalendarEvent, Schedule models
│   ├── events_api.py         # Calendar data fetching
│   ├── prioritizer_agent.py  # Event importance ranking
│   └── scheduler_agent.py    # Schedule optimization
├── location/                  # Location services
│   ├── model.py              # Location type hierarchy, NAMED_LOCATIONS
│   └── resolver_agent.py     # Address to coordinate resolution
├── weather/                   # Weather analysis
│   ├── model.py              # WeatherReport, WeatherAnalysis
│   ├── weather_api.py        # Pirate Weather integration
│   ├── meteorologist_agent.py # Weather interpretation
│   └── sunset_oracle_agent.py # Sunset quality prediction
├── tools/                     # External service clients
│   ├── hass_api.py           # Home Assistant integration
│   └── geocoding_api.py      # Google Maps integration
├── cli/                       # Command-line interface
│   ├── briefing.py           # Main briefing command
│   ├── audio.py              # Audio-related commands
│   └── prompts.py            # Langfuse prompt commands
├── workflow.py               # Main LangGraph workflow definition
├── state.py                  # Central State model
├── paths.py                  # File path utilities, BriefingDirectory
├── env.py                    # Environment configuration
├── llm.py                    # AI model configuration
└── tts.py                    # Text-to-speech orchestration

tests/                        # Test files mirroring src structure
├── test_id3_tags.py
├── test_weather_api.py
└── ...

scripts/
├── fmt.sh                    # Code formatting script
└── ...

src/pirate_weather_api_client/ # Generated OpenAPI client
```

**Key Files:**
- `workflow.py` - Entry point for understanding the main pipeline
- `state.py` - Central state definition showing all data flow
- `paths.py` - File I/O patterns and directory management
- `brief/model.py` - Core script data structures
- `audio/workflow.py` - TTS subgraph implementation

## Architecture Overview

### Workflow Orchestration (LangGraph)
The project uses LangGraph for orchestrating complex AI-driven workflows. Key workflow is in `src/lmnop_wakeup/workflow.py`:

- **State-driven execution**: Central `State` model accumulates data through workflow stages
- **Parallel processing**: Concurrent location resolution and weather analysis using `Send` operations
- **Checkpointing**: PostgreSQL-backed persistence allows workflow resume
- **Multi-tier caching**: Redis + SQLite caching for expensive operations

**Main workflow stages:**
1. `populate_raw_inputs` → `process_location` (parallel) → `fork_analysis`
2. Parallel: `calculate_schedule` + `analyze_weather` + `predict_sunset_beauty`
3. `prioritize_events` → `write_content_optimization` → `write_briefing_script` → `consolidate_dialogue`

### Agent-Based Architecture
Standardized AI agent pattern using `LmnopAgent` wrapper around pydantic-ai:

- **Location agents**: `src/lmnop_wakeup/location/resolver_agent.py` - Address to coordinate resolution
- **Weather agents**: `src/lmnop_wakeup/weather/meteorologist_agent.py`, `sunset_oracle_agent.py` - Weather analysis and sunset prediction
- **Event agents**: `src/lmnop_wakeup/events/prioritizer_agent.py`, `scheduler_agent.py` - Event prioritization and scheduling
- **Content agents**: `src/lmnop_wakeup/brief/script_writer_agent.py`, `content_optimizer.py` - Script generation and optimization

All agents follow pattern: type-safe input/output, Langfuse prompt integration, automatic tracing.

### Data Model Patterns
**Domain-driven bounded contexts:**

- **Events**: `CalendarEvent`, `Schedule`, `CalendarsOfInterest` in `src/lmnop_wakeup/events/model.py`
- **Weather**: `WeatherReport`, `WeatherAnalysis`, `RegionalWeatherReports` in `src/lmnop_wakeup/weather/model.py`
- **Location**: Type hierarchy `Location` → `CoordinateLocation` → `ResolvedLocation` → `NamedLocation` in `src/lmnop_wakeup/location/model.py`
- **Briefing**: `BriefingScript`, `Character` models in `src/lmnop_wakeup/brief/model.py`

Data flows through workflow as additive State updates using `Annotated` aggregation fields.

### External Service Integration
**Well-abstracted API clients:**

- Google Calendar + Home Assistant calendars
- Pirate Weather API (custom client in `src/pirate_weather_api_client/`)
- Google Geocoding/Routes for location resolution
- Google Gemini AI for multiple specialized agents
- Text-to-speech synthesis with character voices

### Audio/TTS Pipeline
Sophisticated multi-character voice synthesis in `src/lmnop_wakeup/audio/`:

- Character-based voice mapping with distinct personalities
- Audio file management and concatenation
- Rate-limited API integration
- Master audio track generation
- ID3 tagging for podcast metadata (title, artist, album, cover art)
  - Tags added to both intermediate (`briefing.mp3`) and final (`master_briefing.mp3`) files
  - Podcast cover art embedded from `src/lmnop_wakeup/audio/cover.png`
  - Full script included in comment field for debugging

## Project-Specific Patterns

### Environment Configuration
- Uses `opr` (1Password CLI) for secure API key management
- Environment setup in `src/lmnop_wakeup/env.py`
- Type-safe configuration with validation

**Environment Variables:**
- `LOG_LEVEL` - Controls overall logging verbosity (TRACE, DEBUG, INFO, WARNING, ERROR)
- `LANGRAPH_DEBUG` - Controls Langraph state dumping (true/false, default: false)

### Caching Strategy
Multi-tier caching approach:
- Redis for shared/persistent data (`aiocache` integration)
- SQLite for workflow caching
- Function-level TTL caching with decorators

### Location Handling
Named locations defined in `src/lmnop_wakeup/location/model.py`:
- `LocationName.home` - Primary user location
- Strong typing prevents coordinate/address confusion
- Distance-based weather fetching logic

### Testing Patterns
- Async test patterns using `pytest-asyncio`
- Integration tests with external APIs
- Workflow state testing

### File Organization
- `src/lmnop_wakeup/core/` - Shared utilities (logging, caching, typing, date handling)
- `src/lmnop_wakeup/tools/` - External service integrations
- `src/lmnop_wakeup/paths.py` - Type-safe file path management for briefing outputs
- Generated briefings saved to `BriefingDirectory` with JSON + audio outputs

When making changes, follow the domain boundaries and use existing agent patterns. All AI interactions should use the `LmnopAgent` wrapper for consistency.

## Code Style Guidelines

- **No explanatory comments**: Avoid comments that explain what was done during refactoring (e.g., "TTS is now handled automatically")
- **Comments explain WHY, not WHAT**: Only add comments that provide context future maintainers need
- **Self-documenting code**: Prefer clear naming and structure over explanatory comments

## Recent Architecture Changes (June 2025)

### TTS Integration into Workflow Graph
- TTS generation moved from separate CLI step into main workflow graph
- Runs automatically after `consolidate_dialogue` node
- No manual confirmation needed in CLI
- Audio files tracked in `State.tts: TTSState`
- Checkpointing works for TTS operations
- TTS subgraph uses minimal `TTSWorkflowState` for modularity

### Thread Management & Checkpointing
- Thread IDs now support continuation of incomplete workflows
- CLI `--thread-id` parameter for explicit thread control
- Auto-discovery of incomplete threads for seamless resume
- PostgreSQL-backed checkpoint persistence

### Script Consolidation & Event Filtering (June 2025)
**Enhanced Multi-Speaker TTS Optimization:**
- `BriefingScript.consolidate_dialogue()` now uses two-step process:
  1. First merges consecutive lines by same speaker with identical style directions
  2. Then groups merged lines into speaker segments (1-2 speakers max) for TTS
- Added `_merge_consecutive_same_speaker_lines()` helper that combines text with proper spacing
- Significantly reduces Gemini TTS API calls while maintaining natural dialogue flow

**Event Filtering Pipeline:**
- `CalendarsOfInterest.filter_by_event_ids()` filters calendars to only specified events
- `event_ids` properties on `PrioritizedEvents` and `ContentOptimizationReport` return all contained event IDs
- `ScriptWriterInput` now includes filtered `CalendarsOfInterest` field
- Events serialized as markdown (not JSON) for better LLM comprehension
- Clean data flow: event prioritization → content optimization → calendar filtering → script generation

**Natural Language Timing:**
- Enhanced `when_colloquial` field descriptions across all event models
- Contains natural timing references like "tomorrow morning", "this afternoon", "next Tuesday"
- Downstream models copy these from original `CalendarEvent.when_colloquial` field
- Enables conversational script generation with natural timing references

### ID3 Tagging (July 2025)
**Podcast Metadata for Music Assistant:**
- `BriefingID3Tags` model encapsulates all podcast metadata
- ID3Tagger class handles eyeD3 integration for MP3 tagging
- Tags include: title with date, artist ("lmnop"), album ("Daily Briefings"), genre, cover art
- Full briefing script embedded in comment field as markdown
- Cover art loaded from `src/lmnop_wakeup/audio/cover.png`
- Applied during audio mastering and production mixing stages

## Interaction Guidelines
- Always number your questions for easier answering
