from datetime import date

from fastapi import BackgroundTasks, FastAPI
from loguru import logger
from pydantic import BaseModel

from .services.briefing_service import BriefingService

app = FastAPI(title="Wakeup Briefing API", version="1.0.0")


class GenerateRequest(BaseModel):
  briefing_date: date


class AnnounceRequest(BaseModel):
  briefing_date: date


briefing_service = BriefingService()


@app.post("/generate")
async def generate_briefing(request: GenerateRequest, background_tasks: BackgroundTasks):
  """Generate a briefing script and voiceover for the specified date."""
  logger.info("Received generate request for {date}", date=request.briefing_date)

  # Return immediately and process in background
  background_tasks.add_task(_generate_briefing_background, request.briefing_date)

  return {"status": "accepted", "briefing_date": request.briefing_date}


@app.post("/announce")
async def announce_briefing(request: AnnounceRequest):
  """Announce a briefing for the specified date."""
  logger.info("Received announce request for {date}", date=request.briefing_date)

  # Just accept the parameter and return success
  return {"status": "accepted", "briefing_date": request.briefing_date}


async def _generate_briefing_background(briefing_date: date) -> None:
  """Background task to generate briefing."""
  try:
    logger.info("Starting background briefing generation for {date}", date=briefing_date)
    output_path = await briefing_service.generate_briefing(briefing_date)
    logger.info("Background briefing generation completed: {path}", path=output_path)
  except Exception as e:
    logger.error(
      "Background briefing generation failed for {date}: {error}", date=briefing_date, error=str(e)
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
