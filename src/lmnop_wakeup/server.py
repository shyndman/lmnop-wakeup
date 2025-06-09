from datetime import date

import structlog
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .audio.announcer import (
  AnnouncementFailedError,
  BriefingAnnouncer,
  MusicAssistantConnectionError,
  PlayerNotFoundError,
)
from .brief.service import BriefingService
from .env import (
  get_music_assistant_player_id,
  get_music_assistant_url,
  get_wakeup_server_base_url,
)
from .paths import BriefingDirectory

logger = structlog.get_logger()

app = FastAPI(title="Wakeup Briefing API", version="1.0.0")


class GenerateRequest(BaseModel):
  briefing_date: date
  thread_id: str | None = None


class AnnounceRequest(BaseModel):
  briefing_date: date
  player_id: str | None = None


briefing_service = BriefingService()


@app.post("/generate")
async def generate_briefing(request: GenerateRequest):
  """Generate a briefing script and voiceover for the specified date."""
  logger.info(f"Received generate request for {request.briefing_date}")

  try:
    # Wait for generation to complete
    result = await briefing_service.generate_briefing(
      request.briefing_date, thread_id=request.thread_id
    )

    logger.info(f"Briefing generation completed successfully for {request.briefing_date}")
    return {
      "status": "success",
      "briefing_date": request.briefing_date,
      "output_path": str(result.output_path),
      "schedule": result.schedule,
    }

  except Exception as e:
    logger.exception(f"Briefing generation failed for {request.briefing_date}: {e}")
    raise HTTPException(
      status_code=500,
      detail={
        "status": "error",
        "error_code": "generation_failed",
        "message": f"Briefing generation failed: {str(e)}",
        "briefing_date": str(request.briefing_date),
        "technical_details": {"exception": type(e).__name__},
      },
    )


@app.post("/announce")
async def announce_briefing(request: AnnounceRequest):
  """Announce a briefing for the specified date.

  If player_id is provided in the request, it will override the environment configuration.
  """
  logger.info(f"Received announce request for {request.briefing_date}")

  try:
    # Check if briefing audio exists
    briefing_dir = BriefingDirectory.for_date(request.briefing_date)
    if not briefing_dir.has_master_audio():
      raise HTTPException(
        status_code=404,
        detail={
          "status": "error",
          "error_code": "audio_file_not_found",
          "message": f"No briefing audio found for {request.briefing_date}",
          "briefing_date": str(request.briefing_date),
        },
      )

    # Get environment configuration
    try:
      music_assistant_url = get_music_assistant_url()
      server_base_url = get_wakeup_server_base_url()

      # Use player_id from request if provided, otherwise get from environment
      if request.player_id is not None:
        player_id = request.player_id
        logger.info(f"Using player_id from request: {player_id}")
      else:
        player_id = get_music_assistant_player_id()
        logger.info(f"Using player_id from environment: {player_id}")

    except EnvironmentError as e:
      logger.error(f"Configuration error: {e}")
      raise HTTPException(
        status_code=500,
        detail={
          "status": "error",
          "error_code": "configuration_error",
          "message": f"Server configuration error: {str(e)}",
          "briefing_date": str(request.briefing_date),
          "technical_details": {"error": str(e)},
        },
      )

    # Construct the briefing URL
    briefing_url = f"{server_base_url}/briefing/{request.briefing_date}/audio"

    # Create announcer and play briefing
    announcer = BriefingAnnouncer(music_assistant_url, player_id)

    try:
      success = await announcer.announce(briefing_url)

      if success:
        logger.info(f"Announcement completed successfully for {request.briefing_date}")
        return {
          "status": "success",
          "briefing_date": str(request.briefing_date),
          "message": "Announcement completed successfully",
          "player_id": player_id,
        }
      else:
        # This shouldn't happen given our implementation, but just in case
        raise HTTPException(
          status_code=500,
          detail={
            "status": "error",
            "error_code": "announcement_failed",
            "message": "Announcement failed for unknown reason",
            "briefing_date": str(request.briefing_date),
          },
        )

    except MusicAssistantConnectionError as e:
      logger.error(f"Music Assistant connection failed: {e}")
      raise HTTPException(
        status_code=503,
        detail={
          "status": "error",
          "error_code": "music_assistant_connection_failed",
          "message": f"Failed to connect to Music Assistant: {str(e)}",
          "briefing_date": str(request.briefing_date),
          "technical_details": {
            "music_assistant_url": music_assistant_url,
            "player_id": player_id,
            "exception": type(e).__name__,
          },
        },
      )

    except PlayerNotFoundError as e:
      logger.error(f"Player configuration error: {e}")
      raise HTTPException(
        status_code=500,
        detail={
          "status": "error",
          "error_code": "player_configuration_error",
          "message": f"Player configuration error: {str(e)}",
          "briefing_date": str(request.briefing_date),
          "technical_details": {
            "music_assistant_url": music_assistant_url,
            "player_id": player_id,
            "exception": type(e).__name__,
          },
        },
      )

    except AnnouncementFailedError as e:
      logger.error(f"Announcement failed: {e}")
      raise HTTPException(
        status_code=500,
        detail={
          "status": "error",
          "error_code": "announcement_failed",
          "message": f"Announcement failed: {str(e)}",
          "briefing_date": str(request.briefing_date),
          "technical_details": {
            "music_assistant_url": music_assistant_url,
            "player_id": player_id,
            "briefing_url": briefing_url,
            "exception": type(e).__name__,
          },
        },
      )

  except HTTPException:
    # Re-raise HTTP exceptions as-is
    raise
  except Exception as e:
    # Catch any other unexpected errors
    logger.exception(f"Unexpected error during announcement: {e}")
    raise HTTPException(
      status_code=500,
      detail={
        "status": "error",
        "error_code": "unexpected_error",
        "message": f"Unexpected server error: {str(e)}",
        "briefing_date": str(request.briefing_date),
        "technical_details": {"exception": type(e).__name__},
      },
    )


async def _generate_briefing_background(briefing_date: date) -> None:
  """Background task to generate briefing."""
  try:
    logger.info(f"Starting background briefing generation for {briefing_date}")
    result = await briefing_service.generate_briefing(briefing_date)
    logger.info(f"Background briefing generation completed: {result.output_path}")
  except Exception:
    logger.exception(f"Background briefing generation failed for {briefing_date}")


@app.get("/briefing/{briefing_date}/audio")
async def serve_briefing_audio(briefing_date: date):
  """Serve the master briefing audio file for the specified date."""
  briefing_dir = BriefingDirectory.for_date(briefing_date)

  if not briefing_dir.has_master_audio():
    raise HTTPException(
      status_code=404,
      detail={
        "status": "error",
        "error_code": "audio_file_not_found",
        "message": f"No briefing audio found for {briefing_date}",
        "briefing_date": str(briefing_date),
      },
    )

  return FileResponse(
    path=briefing_dir.master_audio_path,
    media_type="audio/mpeg",
    filename=f"briefing_{briefing_date}.mp3",
  )


@app.get("/health")
async def health_check():
  """Health check endpoint."""
  return {"status": "healthy"}


async def run() -> None:
  """Main server entry point."""
  import uvicorn

  logger.info("Starting Wakeup Briefing API server")
  config = uvicorn.Config(
    app=app,
    host="0.0.0.0",
    port=8002,
    log_config=None,
    log_level=None,
  )
  server = uvicorn.Server(config)
  await server.serve()
