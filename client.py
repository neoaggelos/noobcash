#!/usr/bin/env python3
'''
Usage:
    $ client.py [127.0.0.1] [8000] [--coordinator]
'''

import os
import sys
import requests
import argparse

BASE_DIR = os.path.dirname(__file__)
sys.path.append(BASE_DIR)
from noobcash.backend import settings

# parse arguments
parser = argparse.ArgumentParser()
parser.add_argument('host', help='hostname announced to the coordinator, e.g. "127.0.0.1"', type=str)
parser.add_argument('port', help='port to use, e.g. "8000"', type=int)
parser.add_argument('-n', help='Init as coordinator, for N partipipants', type=int)
args = parser.parse_args()

HOST_FOR_COORDINATOR = f'http://{args.host}:{args.port}'
HOST = f'http://127.0.0.1:{args.port}'
PORT = str(args.port)
PARTICIPANTS = args.n

################################################################################

help_message = '''
Usage:

$ client.py HOST PORT           Start as participant
$ client.py HOST PORT -n N      Start as coordinator, for N participants

Available commands:

* `t [recepient_id] [amount]`   Send `amount` NBC to `recepient`
* `source [fname]`              Read and send transactions from `fname`
* `view`                        View transactions of the latest block
* `balance`                     View balance of each wallet (as of last validated block)
* `help`                        Print this help message
* `exit`                        Exit client (will not stop server)

Extra commands:

* `view_all`                    View transactions of all validated blocks so far
* `latest_balance`              View balance of each wallet (as of last received transaction)
'''

################################################################################

# init participant
API = f'{HOST}/init_server/' if PARTICIPANTS else f'{HOST}/init_client/'

try:
    response = requests.post(API, {
        'num_participants': PARTICIPANTS,
        'host': HOST_FOR_COORDINATOR
    })
    assert response.status_code == 200
except Exception as e:
    print(f'Could not connect to {HOST}: {e.__class__.__name__}: {e}')
    exit(-1)

# store returned token, will be used for sending transactions
TOKEN = response.text

################################################################################

# Enter main loop
while True:
    cmd = input("> ")
    print(cmd)

    if cmd == 'balance':
        # print list of participants with their balance as of the last validated block
        balance = requests.get(f'{HOST}/get_balance/').json()

        for id, p in balance.items():
            print(f'{"* " if p["this"] else "  "}{id}\t({p["pubkey"][100:120]})\t{p["host"]}\t{p["amount"]}\tNBC')

    elif cmd == 'latest_balance':
        # print list of participants with their balance as of last valid transaction
        balance = requests.get(f'{HOST}/get_balance_latest/').json()

        for id, p in balance.items():
            print(f'{"* " if p["this"] else "  "}{id}\t({p["pubkey"][100:120]})\t{p["host"]}\t{p["amount"]}\tNBC')

    elif cmd == 'view':
        # print list of transactions from last validated block
        API = f'{HOST}/get_transactions/'
        transactions = requests.get(API).json()['transactions']

        for tx in transactions:
            print(f'{tx["sender_id"]}\t->\t{tx["recepient_id"]}\t{tx["amount"]}\tNBC\t{tx["id"][:10]}')

    elif cmd == 'view_all':
        # print list of transactions from all blocks
        API = f'{HOST}/get_transactions_all/'
        blocks = requests.get(API).json()['blocks']
        for b in blocks:
            print(f'\nBlock {b["index"]}: (SHA: {b["hash"][:15]}\tPREV: {b["prev"][:15]})')

            for tx in b['transactions']:
                print(f'{tx["sender_id"]}\t->\t{tx["recepient_id"]}\t{tx["amount"]}\tNBC\t{tx["id"][:10]}')

    elif cmd.startswith('t'):
        # create a new transaction
        parts = cmd.split()

        try:
            participants = requests.get(f'{HOST}/get_balance/').json()
            recepient = participants[parts[1]]['pubkey']
            amount = parts[2]
        except:
            continue

        API = f'{HOST}/create_transaction/'
        response = requests.post(API, {
            'token': TOKEN,
            'recepient': recepient,
            'amount': amount
        })

        if response.status_code == 200:
            print('OK.')
        else:
            print(f'Error: {response.text}')
    
    elif cmd.startswith('source'):
        # read file of transactions
        parts = cmd.split()
        participants = requests.get(f'{HOST}/get_balance/').json()

        try:
            fname = parts[1]
            with open(fname, 'r') as fin:
                for line in fin:
                    idx, amount = line.split()
                    recepient = participants[idx[2:]]['pubkey']

                    API = f'{HOST}/create_transaction/'
                    response = requests.post(API, {
                        'token': TOKEN,
                        'recepient': recepient,
                        'amount': amount
                    })

                    if response.status_code == 200:
                        print('OK.')
                    else:
                        print(f'Error: {response.text}')
        except Exception as e:
            print(f'error: {e.__class__.__name__}: {e}')

    elif cmd == 'num_blocks':
        API = f'{HOST}/get_num_blocks_created/'
        response = requests.get(API)

        if response.status_code == 200:
            print('Created', response.json()['num_blocks'], 'blocks in total')
        else:
            print('Error')

    elif cmd == 'num_pending':
        API = f'{HOST}/get_num_pending_transactions/'
        response = requests.get(API)

        if response.status_code == 200:
            print(response.json()['num_pending'], 'pending transactions')
        else:
            print('Error')

    elif cmd == 'help':
        print(help_message)

    elif cmd == 'exit':
        exit(-1)

    else:
        print(f'{cmd}: Unknown command. See `help`')
