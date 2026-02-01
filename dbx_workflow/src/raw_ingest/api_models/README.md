# Auto-generated API Models

This directory contains Pydantic models automatically generated from Coinbase and Frankfurter API responses.

## Purpose

These models are used to detect schema changes via the daily GitHub Action `daily_schema_check.yml`.
The workflow runs `dbx_workflow/scripts/check_api_schemas.py` which:
1. Fetches the latest JSON response from the APIs.
2. Generates Pydantic models using `datamodel-code-generator`.
3. Compares the generated models with the ones in this directory.

If changes are detected, a Pull Request is automatically created to notify the team.

## Usage

These models are primarily for monitoring purposes and are not currently used in the main ingestion pipeline (`CoinbaseFetcher`, `FrankfurterFetcher`), which uses manual parsing for performance and robustness.

**Do not edit these files manually.** They will be overwritten by the automated process.
