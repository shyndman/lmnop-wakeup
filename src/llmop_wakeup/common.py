from datetime import date as Date
from datetime import datetime as DateTime
from typing import NewType

from pydantic import BaseModel

ApiKey = NewType("ApiKey", str)


class TimeInfo(BaseModel):
  date: Date | None = None
  dateTime: DateTime | None = None

  # Validate that one and only one is provided
  def model_post_init(self, __context):
    if (self.date is None and self.dateTime is None) or (
      self.date is not None and self.dateTime is not None
    ):
      raise ValueError("Either 'date' or 'dateTime' must be provided, but not both")
