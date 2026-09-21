"""
Entry point for the Cloud Invoice Sync job.

Flow:
  1. Search the Gmail inbox for recent emails with PDF attachments.
  2. For each email, match it to a known cloud provider (sender + subject).
  3. Download each PDF attachment and parse the billing period / amount.
  4. Upload to Drive under Cloud_Invoices/<Provider>/<Year>/, skipping files
     that already exist there.

Required environment variables:
  GMAIL_OAUTH_JSON      - JSON string with client_id/client_secret/refresh_token
  DRIVE_ROOT_FOLDER_ID  - Drive folder ID for the Cloud_Invoices root folder
"""
import logging
import os
import sys

from gmail_client import GmailClient
from drive_client import DriveClient
from providers import match_provider
from pdf_parser import extract_text, parse_billing_period, parse_amount, fallback_period

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger("cloud-invoice-sync")

# Adjust the lookback window if invoices are sometimes processed late.
GMAIL_SEARCH_QUERY = "has:attachment filename:pdf newer_than:30d"


def build_filename(provider_name: str, year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}_{provider_name}_Invoice.pdf"


def process_message(gmail: GmailClient, drive: DriveClient, message_stub: dict) -> bool:
    """Process a single Gmail message. Returns True if at least one PDF was
    uploaded or already present in Drive; False if the message was skipped
    (no provider match or no PDF attachment)."""
    message = gmail.get_message(message_stub["id"])
    sender = gmail.get_header(message, "From") or ""
    subject = gmail.get_header(message, "Subject") or ""

    provider = match_provider(sender, subject)
    if not provider:
        logger.info(f"No provider match — from='{sender}' subject='{subject}'")
        return False

    attachments = gmail.get_pdf_attachments(message)
    if not attachments:
        logger.info(f"No PDF attachment on matched {provider.name} email — subject='{subject}'")
        return False

    handled_any = False

    for attachment in attachments:
        pdf_bytes = gmail.download_attachment(message["id"], attachment["attachment_id"])
        text = extract_text(pdf_bytes)

        year, month = parse_billing_period(text, provider.period_patterns)
        if year == 0 or month == 0:
            logger.warning(
                f"PDF period parsed as 0-0 (unknown) for {provider.name} — "
                f"falling back to previous month. subject='{subject}'"
            )
            year, month = fallback_period()

        amount = parse_amount(text, provider.amount_patterns)
        if amount:
            logger.info(f"Parsed amount for {provider.name} {year}-{month:02d}: {amount}")

        filename = build_filename(provider.name, year, month)
        folder_id = drive.get_provider_year_folder(provider.name, year)

        if drive.file_exists(filename, folder_id):
            logger.info(f"Skipped (already exists): {filename}")
            handled_any = True
            continue

        drive.upload_pdf(filename, pdf_bytes, folder_id)
        logger.info(f"Uploaded {filename}")
        handled_any = True

    return handled_any


def main() -> int:
    gmail_oauth_json = os.environ.get("GMAIL_OAUTH_JSON")
    drive_root_folder_id = os.environ.get("DRIVE_ROOT_FOLDER_ID")

    if not gmail_oauth_json or not drive_root_folder_id:
        logger.error("Missing required environment variables: GMAIL_OAUTH_JSON, DRIVE_ROOT_FOLDER_ID")
        return 1

    gmail = GmailClient(gmail_oauth_json)
    drive = DriveClient(gmail_oauth_json, drive_root_folder_id)

    messages = gmail.search_invoice_emails(GMAIL_SEARCH_QUERY)
    logger.info(f"Found {len(messages)} candidate email(s) to check")

    if not messages:
        logger.warning("No candidate invoice emails found in this run")
        return 0

    processed = 0
    for message_stub in messages:
        try:
            if process_message(gmail, drive, message_stub):
                processed += 1
        except Exception:
            logger.exception(f"Failed to process message {message_stub.get('id')}")

    logger.info(f"Sync complete — processed={processed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
