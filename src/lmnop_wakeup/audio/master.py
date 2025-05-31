from functools import reduce
from pathlib import Path
from typing import cast


def master_briefing_audio(path: Path):
  from pydub import AudioSegment

  wav_files = list(path.glob("*.wav"))
  wav_files.sort(key=lambda f: int(f.stem))  # Sort by filename stem

  audio_segments = cast(
    list[AudioSegment], map(lambda wav: AudioSegment.from_wav(str(wav)), wav_files)
  )
  combined_segments = reduce(lambda x, y: x + y, audio_segments)
  combined_segments.export(path / "master_briefing.mp3", "mp3")
