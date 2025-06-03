from datetime import date
from pathlib import Path

from loguru import logger

from ..brief.model import BriefingScript
from ..core.cache import get_cache
from ..core.paths import get_data_path
from ..env import assert_env
from ..location.model import CoordinateLocation, LocationName, location_named
from ..tts import run_voiceover


class BriefingService:
  def __init__(self):
    self.default_location = location_named(LocationName.home)

  async def generate_briefing(
    self,
    briefing_date: date,
    location: CoordinateLocation | None = None,
    review_events: bool = False,
  ) -> Path:
    """Generate a briefing script and voiceover for the given date and location."""
    from ..workflow import Run, run_workflow_command

    location = location or self.default_location

    logger.info(
      "Starting briefing generation for {date} at {location}", date=briefing_date, location=location
    )

    async with get_cache():
      assert_env()

      cmd = Run(
        briefing_date=briefing_date,
        briefing_location=location,
        review_events=review_events,
      )

      briefing_script = await run_workflow_command(cmd)

      if briefing_script is None:
        raise ValueError("Failed to generate briefing script")

      output_path = self._prepare_output_path(briefing_date)

      logger.info("Generating voiceover for briefing")
      await run_voiceover(briefing_script, print_script=False, output_path=output_path)

      logger.info("Briefing generation complete: {path}", path=output_path)
      return output_path

  def _prepare_output_path(self, briefing_date: date) -> Path:
    """Prepare the output directory for the briefing."""
    path = get_data_path() / briefing_date.isoformat()
    path.mkdir(parents=True, exist_ok=True)
    return path

  def load_briefing_script(self, briefing_date: date) -> BriefingScript:
    """Load an existing briefing script from disk."""
    path = get_data_path() / briefing_date.isoformat()
    brief_path = path / "brief.json"

    if not brief_path.exists():
      raise FileNotFoundError(f"No briefing found for {briefing_date}")

    brief_content = brief_path.read_text()
    return BriefingScript.model_validate_json(brief_content)
