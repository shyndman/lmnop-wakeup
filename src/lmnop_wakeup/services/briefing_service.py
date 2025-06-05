from dataclasses import dataclass
from datetime import date
from pathlib import Path

import structlog

from ..brief.model import BriefingScript
from ..core.cache import get_cache
from ..env import assert_env
from ..events.model import Schedule
from ..location.model import CoordinateLocation, LocationName, location_named
from ..paths import BriefingDirectory
from ..tts import run_voiceover

logger = structlog.get_logger(__name__)


@dataclass
class BriefingResult:
  """Result of briefing generation including output path and schedule."""

  output_path: Path
  schedule: Schedule | None


class BriefingService:
  def __init__(self):
    self.default_location = location_named(LocationName.home)

  async def generate_briefing(
    self,
    briefing_date: date,
    location: CoordinateLocation | None = None,
    review_events: bool = False,
  ) -> BriefingResult:
    """Generate a briefing script and voiceover for the given date and location."""
    from ..workflow import run_workflow_command

    location = location or self.default_location

    logger.info(f"Starting briefing generation for {briefing_date} at {location}")

    async with get_cache():
      assert_env()

      briefing_script, final_state = await run_workflow_command(
        briefing_date=briefing_date,
        briefing_location=location,
      )

      if briefing_script is None:
        raise ValueError("Failed to generate briefing script")

      output_path = self._prepare_output_path(briefing_date)

      logger.info("Generating voiceover for briefing")
      await run_voiceover(briefing_script, print_script=False, output_path=output_path)

      logger.info(f"Briefing generation complete: {output_path}")
      return BriefingResult(output_path=output_path, schedule=final_state.schedule)

  def _prepare_output_path(self, briefing_date: date) -> Path:
    """Prepare the output directory for the briefing."""
    briefing_dir = BriefingDirectory.for_date(briefing_date)
    briefing_dir.ensure_exists()
    return briefing_dir.base_path

  def load_briefing_script(self, briefing_date: date) -> BriefingScript:
    """Load an existing briefing script from disk."""
    briefing_dir = BriefingDirectory.for_date(briefing_date)
    return briefing_dir.load_script()
