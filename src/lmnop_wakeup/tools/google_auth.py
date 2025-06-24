"""Common Google API authentication module."""

import os.path

import structlog
from google.auth.external_account_authorized_user import Credentials as ExternalCredentials
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

logger = structlog.get_logger()

# If modifying these scopes, delete the file token.json.
SCOPES = [
  "https://www.googleapis.com/auth/calendar.readonly",
  "https://www.googleapis.com/auth/calendar.events",
  "https://www.googleapis.com/auth/tasks.readonly",
  "https://www.googleapis.com/auth/tasks",
]


def authenticate() -> Credentials | ExternalCredentials:
  """Returns Google API credentials, sending the user to SSO if required."""
  credentials = None

  # The file token.json stores the user's access and refresh tokens, and is created automatically
  # when the authorization flow completes for the first time.
  if os.path.exists(".google/token.json"):
    logger.debug("Loading credentials from token.json")
    credentials = Credentials.from_authorized_user_file(".google/token.json", SCOPES)
  else:
    logger.warning(
      "No token.json file found. Please run the script to authenticate with Google APIs.",
    )

  # No valid credentials available, let the user log in.
  if not credentials or not credentials.valid:
    try:
      if credentials and credentials.expired and credentials.refresh_token:
        logger.debug("Refreshing expired credentials")
        credentials.refresh(Request())
    except Exception:
      credentials = None
      logger.exception("Failed to refresh credentials, requesting new ones")

    if not credentials or not credentials.valid:
      logger.debug("No valid credentials, requesting new ones")
      flow = InstalledAppFlow.from_client_secrets_file(".google/credentials.json", SCOPES)
      credentials = flow.run_local_server(port=0)

    # Save the credentials for the next run
    logger.debug("Saving credentials to token.json")
    with open(".google/token.json", "w") as token:
      token.write(credentials.to_json())

  return credentials
