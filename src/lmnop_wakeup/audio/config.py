import dataclasses


@dataclasses.dataclass
class TTSConfig:
  rate_limit_per_minute: float = 4.0
  model_name: str = "gemini-2.5-flash-preview-tts"
  audio_channels: int = 1
  audio_rate: int = 24000
  audio_sample_width: int = 2
  temperature: float = 0.8
  top_p: float = 0.95
