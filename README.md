# Pretix VerDE Bulk Refund

We do events where we collect deposits (e.g., for cups). At the end of the event, people hand back their cups and are refunded the deposit via pretix.

This script does the following:
1. Read a check-in list for the deposit product
2. Cancel the deposit positions

The input file is a Pretix-exported check-in lists with the `CSV (with commas)` format which includes ticket secrets.

To use this script, move `.example.env` to `.env` and fill out the fields. Then run the script. Be sure to test with `--dry-run` first. See `--help` for instructions.
