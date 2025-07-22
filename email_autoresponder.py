"""PhoBoCo Intelligent Email Autoresponder

This script connects to Gmail, scans for unread messages in specific labels,
generates polite and professional replies using OpenAI, and saves those
replies as drafts. Drafts allow a human to review the content before
sending, ensuring quality and accuracy.

Usage:
    python email_autoresponder.py

Prerequisites:
  - A Google Cloud project with the Gmail API enabled.
  - OAuth 2.0 client credentials (stored in ``credentials.json``).
  - The first run will prompt you through a browser to authorize the
    application and will store a ``token.json`` for future runs.
  - An OpenAI API key available in the ``OPENAI_API_KEY`` environment variable.

Environment variables:
    OPENAI_API_KEY   Your OpenAI API key used to call the Chat API.

The script is intentionally simple: it only reads metadata and snippets
from the emails, so no full message bodies are downloaded. It replies to
everyone who sent an email, addressing them directly by the “From” header.
You can further customize the prompt or add additional logic to tailor
responses to your needs.
"""

from __future__ import annotations

import base64
import os
from typing import Dict, List, Optional

import openai
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# If modifying these scopes, delete the token.json file.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
]

# Labels to process. Only unread messages with these labels will be
# considered for drafting responses.
LABELS_TO_PROCESS: List[str] = [
    "Leads_New",
    "Clients_OpenQuestions",
    "Finance_Bookings",
    "Event_Changes",
]


def get_gmail_service() -> "googleapiclient.discovery.Resource":
    """Authenticate and build the Gmail API service.

    Returns
    -------
    Resource
        A Gmail API service resource ready for use.
    """
    creds: Optional[Credentials] = None
    # token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the
    # first time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w", encoding="utf-8") as token_file:
            token_file.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def generate_reply(sender: str, subject: str, body_snippet: str) -> str:
    """Generate an email reply using OpenAI's Chat API.

    Parameters
    ----------
    sender : str
        The full "From" header of the incoming email (may include name and
        address).
    subject : str
        The subject of the incoming email.
    body_snippet : str
        A short snippet of the email body for context.

    Returns
    -------
    str
        The generated reply text.
    """
    # Ensure the OpenAI API key is available
    openai.api_key = os.environ.get("OPENAI_API_KEY")
    if not openai.api_key:
        raise RuntimeError(
            "OPENAI_API_KEY environment variable not set. Please set it before running."
        )

    prompt = (
        "You are an assistant drafting polite, professional email replies for a "
        "photo booth rental company named PhoBoCo. Use the email below as context.\n"
        f"From: {sender}\n"
        f"Subject: {subject}\n"
        "Message snippet:\n"
        f"{body_snippet}\n\n"
        "Craft a concise, friendly response addressing the sender's points and "
        "acknowledging their inquiry. Sign off as 'PhoBoCo Team'."
    )

    # Call the OpenAI ChatCompletion endpoint
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=250,
        temperature=0.5,
    )
    reply_text = response["choices"][0]["message"]["content"].strip()
    return reply_text


def create_message(from_email: str, to_email: str, subject: str, message_text: str) -> Dict[str, str]:
    """Create a draft email message in Gmail API format.

    Parameters
    ----------
    from_email : str
        The email address sending the reply (usually "me" for the authenticated user).
    to_email : str
        The recipient's email address.
    subject : str
        The subject of the original email. "Re: " is automatically prepended.
    message_text : str
        The plain text body of the email.

    Returns
    -------
    Dict[str, str]
        A dictionary with a base64 encoded raw MIME message for the Gmail API.
    """
    import email.message
    msg = email.message.EmailMessage()
    msg["To"] = to_email
    msg["From"] = from_email
    msg["Subject"] = "Re: " + subject
    msg.set_content(message_text)
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    return {"raw": raw}


def process_unread_messages(service) -> None:
    """Process unread emails in specified labels, draft responses, and save them.

    This function iterates over defined labels, fetches unread messages,
    generates replies using OpenAI, and saves the replies as drafts in Gmail.

    Parameters
    ----------
    service : googleapiclient.discovery.Resource
        The authenticated Gmail API service.
    """
    user_id = "me"
    for label in LABELS_TO_PROCESS:
        try:
            # List unread messages with this label
            response = (
                service.users()
                .messages()
                .list(userId=user_id, labelIds=[label], q="is:unread")
                .execute()
            )
            messages = response.get("messages", [])
            for message in messages:
                msg_id = message["id"]
                # Fetch minimal metadata and snippet for context
                full_msg = (
                    service.users()
                    .messages()
                    .get(
                        userId=user_id,
                        id=msg_id,
                        format="metadata",
                        metadataHeaders=["Subject", "From"],
                    )
                    .execute()
                )
                headers = {h["name"]: h["value"] for h in full_msg["payload"].get("headers", [])}
                subject = headers.get("Subject", "")
                sender = headers.get("From", "")
                snippet = full_msg.get("snippet", "")

                reply_body = generate_reply(sender, subject, snippet)
                draft_message = create_message(from_email=user_id, to_email=sender, subject=subject, message_text=reply_body)
                # Save the draft
                service.users().drafts().create(userId=user_id, body={"message": draft_message}).execute()
        except HttpError as error:
            # Print the error but continue processing other labels
            print(f"An error occurred processing label {label}: {error}")


def main() -> None:
    """Entry point for running the autoresponder."""
    service = get_gmail_service()
    process_unread_messages(service)


if __name__ == "__main__":
    main()
