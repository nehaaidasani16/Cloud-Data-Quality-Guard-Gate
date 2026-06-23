"""
Cloud Data Quality Guard Gate.

"""

import boto3
import csv
import os
import logging
from datetime import datetime, timezone


BUCKET_NAME = "cloud-data-quality-check"  # <-- change to your bucket
REMOTE_FILE = "transaction_ledger.csv"
LOCAL_RAW_FILE = "data/incoming_ledger.csv"
QUARANTINE_FILE = "logs/quarantine_report.csv"
CLEAN_FILE = "logs/clean_records.csv"
LOG_FILE = "logs/pipeline_audit.log"

os.makedirs("logs", exist_ok=True)
os.makedirs("data", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("guard_gate")


def download_from_s3(bucket: str, remote_key: str, local_path: str) -> bool:
    """Pull the target file down from S3 using Boto3. Returns True on success."""
    try:
        s3_client = boto3.client("s3")
        logger.info("Connecting to S3 and downloading '%s' from bucket '%s'...", remote_key, bucket)
        s3_client.download_file(bucket, remote_key, local_path)
        logger.info("Download successful -> %s", local_path)
        return True
    except Exception as aws_err:
        logger.error("Cloud connection error while fetching object from S3: %s", aws_err)
        return False


def validate_record(record: dict) -> tuple[bool, str]:
    txn_id = (record.get("transaction_id") or "").strip()
    asset = (record.get("asset_class") or "").strip()
    raw_amount = record.get("notional_amount")

    if not txn_id:
        return False, "Missing transaction_id"

    if not asset:
        return False, "Missing or blank asset_class"

    try:
        amount = float(raw_amount)
    except (ValueError, TypeError):
        return False, f"Non-numeric notional_amount: '{raw_amount}'"

    if amount <= 0:
        return False, f"Non-positive notional_amount: {amount}"

    return True, ""


def execute_cloud_dq_sweep():
    if not download_from_s3(BUCKET_NAME, REMOTE_FILE, LOCAL_RAW_FILE):
        logger.error("Aborting sweep — could not retrieve source file.")
        return

    logger.info("Starting Data Quality Guard Sweep on %s", LOCAL_RAW_FILE)

    clean_records = []
    quarantined_records = []

    with open(LOCAL_RAW_FILE, mode="r", newline="") as f:
        reader = csv.DictReader(f)
        for record in reader:
            is_valid, reason = validate_record(record)
            if is_valid:
                clean_records.append(record)
                logger.info("[CLEAN] %s passed validation.", record.get("transaction_id"))
            else:
                record["rejection_reason"] = reason
                quarantined_records.append(record)
                logger.warning("[QUARANTINED] %s -> %s", record.get("transaction_id"), reason)

    if clean_records:
        with open(CLEAN_FILE, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["transaction_id", "asset_class", "notional_amount"])
            writer.writeheader()
            writer.writerows(clean_records)

    if quarantined_records:
        with open(QUARANTINE_FILE, "w", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=["transaction_id", "asset_class", "notional_amount", "rejection_reason"]
            )
            writer.writeheader()
            writer.writerows(quarantined_records)

    total = len(clean_records) + len(quarantined_records)
    logger.info(
        "Sweep complete at %s | Total: %d | Clean: %d | Quarantined: %d",
        datetime.now(timezone.utc).isoformat(timespec="seconds"),
        total,
        len(clean_records),
        len(quarantined_records),
    )


if __name__ == "__main__":
    execute_cloud_dq_sweep()