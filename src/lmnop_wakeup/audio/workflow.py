from pathlib import Path

import structlog
from langgraph.graph import StateGraph
from pydantic import AwareDatetime, BaseModel

from ..brief.model import ConsolidatedBriefingScript
from ..core.tracing import trace
from ..paths import BriefingDirectory
from ..tts import TTSOrchestrator
from .master import master_briefing_audio
from .production import AudioProductionMixer

logger = structlog.get_logger(__name__)


class TTSState(BaseModel):
  """A model representing the state of TTS generation.
  Tracks individual audio files and the final master audio file.
  """

  generated_audio_files: list[Path] = []
  """List of individual audio files generated for each script line."""

  briefing_audio_path: Path | None = None
  """Path to the intermediate briefing audio file (before theme music)."""

  master_audio_path: Path | None = None
  """Path to the final mastered audio file (with theme music)."""

  audio_production_enabled: bool = True
  """Whether to add audio production to the briefing."""


class TTSWorkflowState(BaseModel):
  """Minimal state for TTS workflow."""

  consolidated_briefing_script: ConsolidatedBriefingScript
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
  """Master the individual TTS files into a single intermediate audio file."""
  logger.info("Starting audio mastering")

  if not state.tts.generated_audio_files:
    raise ValueError("No individual TTS files available for mastering")

  # Determine output path from briefing date
  briefing_date = state.day_start_ts.date()
  briefing_dir = BriefingDirectory.for_date(briefing_date)
  output_path = briefing_dir.base_path

  # Master the audio to intermediate file
  briefing_audio_path = master_briefing_audio(output_path)

  # Set the briefing audio path
  if briefing_audio_path.exists():
    state.tts.briefing_audio_path = briefing_audio_path
    logger.info(f"Intermediate briefing audio created: {briefing_audio_path}")
  else:
    raise ValueError("Briefing audio file was not created successfully")

  return state


@trace()
async def add_audio_production(state: TTSWorkflowState) -> TTSWorkflowState:
  """Add audio production to the briefing audio."""
  logger.info("Starting audio production")

  if not state.tts.briefing_audio_path:
    raise ValueError("No briefing audio file available for audio production")

  if not state.tts.audio_production_enabled:
    logger.info("Audio production disabled, skipping")
    # Copy briefing audio as final master audio
    briefing_date = state.day_start_ts.date()
    briefing_dir = BriefingDirectory.for_date(briefing_date)
    state.tts.master_audio_path = state.tts.briefing_audio_path
    return state

  # Determine paths
  briefing_date = state.day_start_ts.date()
  briefing_dir = BriefingDirectory.for_date(briefing_date)
  master_audio_path = briefing_dir.master_audio_path

  # Mix audio production with briefing audio
  mixer = AudioProductionMixer()
  try:
    final_audio_path = mixer.mix_audio_with_briefing(
      briefing_audio_path=state.tts.briefing_audio_path,
      script=state.consolidated_briefing_script,
      audio_files_dir=briefing_dir.base_path,
      output_path=master_audio_path,
    )
  except FileNotFoundError as e:
    logger.warning(f"Audio production files not found: {e}, skipping audio production")
    # Copy briefing audio as final master audio
    import shutil

    shutil.copy2(state.tts.briefing_audio_path, master_audio_path)
    final_audio_path = master_audio_path

  state.tts.master_audio_path = final_audio_path
  logger.info(f"Audio production completed: {final_audio_path}")

  return state


def build_tts_subgraph() -> StateGraph:
  """Build the TTS subgraph with individual generation, mastering, and audio production nodes."""
  graph_builder = StateGraph(TTSWorkflowState)

  graph_builder.add_node("generate_individual_tts", generate_individual_tts)
  graph_builder.add_node("master_tts_audio", master_tts_audio)
  graph_builder.add_node("add_audio_production", add_audio_production)

  graph_builder.set_entry_point("generate_individual_tts")
  graph_builder.add_edge("generate_individual_tts", "master_tts_audio")
  graph_builder.add_edge("master_tts_audio", "add_audio_production")
  graph_builder.set_finish_point("add_audio_production")

  return graph_builder


# Compile the TTS graph
tts_graph = build_tts_subgraph().compile()
