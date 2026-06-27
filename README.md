# Cloud S3 Data Quality Guard Gate

A Python-based automated data validation pipeline that pulls incoming financial transaction files from an AWS S3 bucket, screens every record against business validation rules, and separates clean records from invalid ones — preventing corrupted data from ever reaching downstream production systems.


## Overview

Financial institutions receive large transaction files daily from external vendors, hedge funds, and clearing houses. These files are dropped into cloud storage (AWS S3) and must be validated before they can safely enter core systems.

This project simulates that real-world pipeline: it connects to AWS S3 using the Boto3 SDK, downloads the incoming ledger file, validates every row against a defined set of business rules, and produces two outputs — a clean file ready for downstream processing, and a quarantine file listing every rejected record with its specific rejection reason — plus a persistent audit log of the entire run.

## Problem Statement

Vendor-submitted financial data is frequently malformed: missing fields, negative trade amounts, non-numeric values, or blank required fields. If this bad data flows directly into a bank's core transactional systems, it can:

- Corrupt daily accounting and reconciliation processes
- Skew risk assessment models
- Produce inaccurate financial reporting
- Trigger costly, manual after-the-fact data fixes

This pipeline acts as a **guard gate** — a screening checkpoint at the edge of the network that catches bad data before it can do damage.

## Architecture

```
 ┌───────────────┐      ┌────────────────┐      ┌─────────────────────┐
 │  Vendor /     │      │   AWS S3       │      │  Local Validation   │
 │  Hedge Fund   │ ───► │   Bucket       │ ───► │  Engine (Python)    │
 │  Source File  │      │ (raw landing)  │      │  via Boto3 SDK      │
 └───────────────┘      └────────────────┘      └─────────┬───────────┘
                                                          │
                                      ┌───────────────────┼───────────────────┐
                                      ▼                                       ▼
                          ┌─────────────────────┐                ┌───────────────────────┐
                          │  clean_records.csv  │                │ quarantine_report.csv │
                          │  (passes all rules) │                │ (flagged + reason)    │
                          └─────────────────────┘                └───────────────────────┘
                                      │
                                      ▼
                          ┌─────────────────────┐
                          │ pipeline_audit.log  │
                          │ (full run history)  │
                          └─────────────────────┘
```

## Tech Stack

| Component         | Tool / Service              |
|-------------------|------------------------------|
| Cloud storage     | AWS S3                       |
| Cloud SDK         | Boto3 (AWS SDK for Python)   |
| Identity & access | AWS IAM (programmatic user)  |
| Language          | Python 3.10+                 |
| Data parsing      | `csv` (standard library)     |
| Logging / audit   | `logging` (standard library) |




The script will:
1. Connect to S3 and download the ledger file
2. Validate every transaction row
3. Write `logs/clean_records.csv` and `logs/quarantine_report.csv`
4. Append a full audit trail to `logs/pipeline_audit.log`

## Validation Rules

| Rule                          | Outcome if violated                    |
|-------------------------------|------------------------------------------|
| `transaction_id` must be present | Record quarantined                    |
| `asset_class` must not be blank  | Record quarantined                    |
| `notional_amount` must be numeric | Record quarantined                   |
| `notional_amount` must be > 0     | Record quarantined                   |

## Sample Output

```
2026-06-24 01:15:51,903 | INFO | Connecting to S3 and downloading 'transaction_ledger.csv' from bucket 'cloud-data-quality-check'...
2026-06-24 01:18:43,175 | INFO | Download successful -> data/incoming_ledger.csv
2026-06-24 01:18:43,202 | INFO | Starting Data Quality Guard Sweep on data/incoming_ledger.csv
2026-06-24 01:18:43,205 | INFO | [CLEAN] TXN_991 passed validation.
2026-06-24 01:18:43,211 | WARNING | [QUARANTINED] TXN_992 -> Non-positive notional_amount: -45000.0
2026-06-24 01:18:43,211 | WARNING | [QUARANTINED] TXN_993 -> Missing or blank asset_class
2026-06-24 01:18:43,211 | INFO | [CLEAN] TXN_994 passed validation.
2026-06-24 01:18:43,229 | WARNING | [QUARANTINED] TXN_995 -> Non-numeric notional_amount: 'abc123'
2026-06-24 01:18:43,229 | INFO | [CLEAN] TXN_996 passed validation.
2026-06-24 01:18:43,229 | WARNING | [QUARANTINED] TXN_997 -> Non-numeric notional_amount: ''
2026-06-24 01:18:43,229 | WARNING | [QUARANTINED] TXN_998 -> Missing or blank asset_class
2026-06-24 01:18:43,238 | INFO | Sweep complete at 2026-06-23T19:48:43+00:00 | Total: 8 | Clean: 3 | Quarantined: 5

```


## Why This Project Matters

In financial technology, the principle is simple: **garbage in, garbage out**. An automated system that blindly processes a trade with a negative amount or a missing required field can trigger reconciliation failures that take engineering and operations teams days to manually untangle.

This project demonstrates the ability to build a *front-door* control — a checkpoint that protects the integrity of downstream systems before bad data ever has a chance to cause damage. That is directly relevant to consulting and banking environments where vendor data quality cannot be guaranteed, and where regulatory compliance depends on demonstrable, auditable data controls.
