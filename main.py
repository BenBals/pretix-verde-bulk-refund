# This is a sample Python script.

# Press ⌃R to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for classes, files, tool windows, actions, and settings.

import os
from dotenv import load_dotenv
import requests
import logging
import datetime
import csv
import argparse
from tqdm import tqdm

load_dotenv()
if not os.path.exists("logs"):
    os.makedirs("logs")
logging.basicConfig(
    filename=f'logs/bulk_refund_{datetime.datetime.now().isoformat()}.log',
    encoding='utf-8',
    level=logging.INFO)

PRETIX_API_KEY = os.getenv('PRETIX_API_KEY')
PRETIX_BASE_URL = os.getenv('PRETIX_BASE_URL')
PRETIX_ORGANIZER = os.getenv('PRETIX_ORGANIZER')
PRETIX_EVENT = os.getenv('PRETIX_EVENT')
CUP_DEPOSIT_PRICE = os.getenv('CUP_DEPOSIT_PRICE')

pretix_event_api_url = f"{PRETIX_BASE_URL}/api/v1/organizers/{PRETIX_ORGANIZER}/events/{PRETIX_EVENT}"
auth_headers = {'Authorization': f'Token {PRETIX_API_KEY}'}


def resolve_ticket_secret_to_position_id(order_code, secret):
    resp = requests.get(f"{pretix_event_api_url}/orders/{order_code}/", headers=auth_headers)

    positions = resp.json()["positions"]

    for position in positions:
        if position["secret"] == secret:
            return position["id"]

    raise Exception(f"[resolve_ticket_secret_to_position_id] Could not resolve order {order_code} with secret {secret}")


def cancel_cup_deposit(cup_deposit_position_id, dry_run=True):
    if not dry_run:
        resp = requests.delete(f"{pretix_event_api_url}/orderpositions/{cup_deposit_position_id}/", headers=auth_headers)
        resp.raise_for_status()

    logging.info(f"[cancel_cup_deposit] Cup deposit {cup_deposit_position_id} successfully canceled")


def find_first_successful_refundable_payment_local_id(order_code):
    resp = requests.get(f"{pretix_event_api_url}/orders/{order_code}/payments/", headers=auth_headers)

    for payment in resp.json()["results"]:
        if payment["state"] == "confirmed" and payment["provider"] != "manual":
            return payment["local_id"]

    raise Exception(f"[find_first_successful_refundable_payment_local_id] Could not find a successfull refunable payment for order {order_code}")


def initiate_cup_deposit_refund(order_code, payment_local_id, dry_run=True):
    if not dry_run:
        resp = requests.post(
            f"{pretix_event_api_url}/orders/{order_code}/payments/{payment_local_id}/refund/",
            data={ "amount": CUP_DEPOSIT_PRICE, "mark_canceled": False },
            headers=auth_headers
        )

        resp.raise_for_status()
    logging.info(f"[initiate_cup_deposit_refund] Refund over €{CUP_DEPOSIT_PRICE} for order {order_code} successfully initiated")


def process_refund(order_code, secret, dry_run=True):
    try:
        cup_deposit_position_id = resolve_ticket_secret_to_position_id(order_code, secret)
        cancel_cup_deposit(cup_deposit_position_id, dry_run=dry_run)
        payment_local_id = find_first_successful_refundable_payment_local_id(order_code)
        initiate_cup_deposit_refund(order_code, payment_local_id, dry_run=dry_run)

        return True
    except Exception as e:
        logging.error(f"[process_refund] Refunding ({order_code}, {secret}) failed with error {e}")
        return False


def file_path(string):
    if os.path.isfile(string):
        return string
    else:
        raise FileNotFoundError(string)

def main():
    parser = argparse.ArgumentParser(
        prog='VerDE Bulk Refunder',
        description='You took a lot of cup deposits, but now you have to give them back')

    parser.add_argument('filepath', type=file_path)  # positional argument
    parser.add_argument('--dry-run', action='store_true')  # option that takes a value
    args = parser.parse_args()

    refund_status = [["Order code", "Secret", "Success?"]]

    with open(args.filepath, newline='') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=',', quotechar='"')
        for row in tqdm(reader):
            if row["Checked in"]:
                order_code = row["Order code"]
                secret = row["Secret"]
                result = process_refund(order_code, secret, dry_run=args.dry_run)
                refund_status += [[order_code, secret, str(result)]]

    with open(f'logs/bulk_refund_{datetime.datetime.now().isoformat()}_status.csv', 'w') as export_file:
        for row in refund_status:
            export_file.write(",".join(row))
            export_file.write("\n")

    return None


if __name__ == '__main__':
    main()
