from pathlib import Path

import structlog
from langgraph.graph import StateGraph
from pydantic import AwareDatetime, BaseModel

from ..brief.model import BriefingScript
from ..core.tracing import trace
from ..paths import BriefingDirectory
from ..tts import TTSOrchestrator
from .master import master_briefing_audio

logger = structlog.get_logger(__name__)


class TTSState(BaseModel):
  """A model representing the state of TTS generation.
  Tracks individual audio files and the final master audio file.
  """

  generated_audio_files: list[Path] = []
  """List of individual audio files generated for each script line."""

  master_audio_path: Path | None = None
  """Path to the final mastered audio file."""


class TTSWorkflowState(BaseModel):
  """Minimal state for TTS workflow."""

  consolidated_briefing_script: BriefingScript
  """The script to convert to audio."""

  day_start_ts: AwareDatetime
  """Used to determine output directory path."""

  tts: TTSState = TTSState()
  """TTS generation state."""


@trace()
async def generate_individual_tts(state: TTSWorkflowState) -> TTSWorkflowState:
  """Generate TTS audio files for individual script lines."""
  logger.info("Starting individual TTS generation")

  # Determine output path from briefing date
  briefing_date = state.day_start_ts.date()
  briefing_dir = BriefingDirectory.for_date(briefing_date)
  briefing_dir.ensure_exists()
  output_path = briefing_dir.base_path

  # Process TTS using existing TTS orchestrator
  orchestrator = TTSOrchestrator()
  await orchestrator.generate_individual_tts_files(state.consolidated_briefing_script, output_path)

  # Collect generated audio files
  audio_files = []
  for i in range(len(state.consolidated_briefing_script.lines)):
    audio_file = output_path / f"{i}.wav"
    if audio_file.exists():
      audio_files.append(audio_file)

  state.tts.generated_audio_files = audio_files
  logger.info(f"Generated {len(audio_files)} individual TTS files")

  return state


@trace()
async def master_tts_audio(state: TTSWorkflowState) -> TTSWorkflowState:
  """Master the individual TTS files into a single audio file."""
  logger.info("Starting audio mastering")

  if not state.tts.generated_audio_files:
    raise ValueError("No individual TTS files available for mastering")

  # Determine output path from briefing date
  briefing_date = state.day_start_ts.date()
  briefing_dir = BriefingDirectory.for_date(briefing_date)
  output_path = briefing_dir.base_path

  # Master the audio
  master_briefing_audio(output_path)

  # Set the master audio path
  master_audio_path = briefing_dir.master_audio_path
  if master_audio_path.exists():
    state.tts.master_audio_path = master_audio_path
    logger.info(f"Master audio created: {master_audio_path}")
  else:
    raise ValueError("Master audio file was not created successfully")

  return state


def build_tts_subgraph() -> StateGraph:
  """Build the TTS subgraph with individual generation and mastering nodes."""
  graph_builder = StateGraph(TTSWorkflowState)

  graph_builder.add_node("generate_individual_tts", generate_individual_tts)
  graph_builder.add_node("master_tts_audio", master_tts_audio)

  graph_builder.set_entry_point("generate_individual_tts")
  graph_builder.add_edge("generate_individual_tts", "master_tts_audio")
  graph_builder.set_finish_point("master_tts_audio")

  return graph_builder


# Compile the TTS graph
tts_graph = build_tts_subgraph().compile()
