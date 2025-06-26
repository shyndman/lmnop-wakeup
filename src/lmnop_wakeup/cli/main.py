"""Main CLI entry point and root command."""

from datetime import date, timedelta

import structlog
from clypi import Command, arg

from ..arg import parse_date_arg
from .audio import Announce, AudioProduction, ListPlayers
from .briefing import LoadData, Script, Server, Voiceover
from .prompts import DumpPrompts
from .tasks import Tasks

logger = structlog.get_logger()


class Wakeup(Command):
  subcommand: (
    Script
    | Voiceover
    | LoadData
    | Server
    | AudioProduction
    | ListPlayers
    | Announce
    | Tasks
    | DumpPrompts
  )

  briefing_date: date = arg(
    default=date.today() + timedelta(days=1),
    parser=parse_date_arg,
    help="the date of the briefing [format: YYYY-MM-DD | +N | today | tomorrow]",
  )


def main():
  try:
    app = Wakeup.parse()
    app.start()
  except KeyboardInterrupt:
    logger.info("lmnop:wakeup was interrupted by the user")
  except Exception:
    logger.exception("Fatal exception")
