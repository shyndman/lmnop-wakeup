import asyncio
from datetime import date

import rich
from pydantic import BaseModel
from rich.markdown import Markdown

from lmnop_wakeup.tools.calendar.model import CalendarSet
from lmnop_wakeup.tools.calendars import get_filtered_calendars_with_notes

from ..common import assert_not_none, get_hass_api_key, get_pirate_weather_api_key
from ..locations import CoordinateLocation, LocationName, location_named
from ..tools.hass_api import get_general_information
from ..tools.weather_api import get_weather_report
from ..tracing import langfuse_span
from ..utils.date import end_of_local_day, start_of_local_day
from .timekeeper import SchedulingDetails, SchedulingInputs, create_timekeeper


class SchedulingInputsSerializer(BaseModel):
  inputs: SchedulingInputs


async def schedule(
  location: CoordinateLocation,
  todays_date: date,
) -> SchedulingDetails:
  console = rich.console.Console()

  with langfuse_span(name="schedule"):
    start_ts = start_of_local_day(todays_date)
    end_ts = end_of_local_day(start_ts)
    hass_token = get_hass_api_key()
    general_info = all_cals = weather = None
    with langfuse_span(name="loading context"):
      general_info, all_cals, weather = await asyncio.gather(
        get_general_information(todays_date=todays_date, hass_api_token=hass_token),
        get_filtered_calendars_with_notes(
          start_ts=start_ts,
          end_ts=end_ts,
          hass_api_token=hass_token,
        ),
        get_weather_report(
          location=location,
          report_start_time=start_ts,
          pirate_weather_api_key=get_pirate_weather_api_key(),
        ),
      )

    timekeeper_agent, instructions, prompt_templates = await create_timekeeper()
    scheduling_inputs = SchedulingInputs(
      home_location=location_named(LocationName.home),
      todays_date=todays_date,
      is_today_workday=general_info.is_today_workday,
      calendars=CalendarSet(calendars=all_cals),
      hourly_weather=weather.get_hourlies_for_day(todays_date, tz=assert_not_none(start_ts.tzinfo)),
    )
    console.print(scheduling_inputs)

    serializer = SchedulingInputsSerializer(inputs=scheduling_inputs)
    model_dump = serializer.model_dump(exclude_unset=True, exclude_none=True)
    console.print(model_dump)
    task_prompt = prompt_templates.format(**model_dump["inputs"])

    with langfuse_span(name="unleash timekeeper"):
      console.print(Markdown(task_prompt))
      schedule = await timekeeper_agent.run(task_prompt, deps=scheduling_inputs)
      return schedule.output
