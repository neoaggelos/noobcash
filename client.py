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

HOST = f'http://{args.host}:{args.port}'
PORT = str(args.port)
PARTICIPANTS = args.n

################################################################################

# init participant
API = f'{HOST}/init_server/' if PARTICIPANTS else f'{HOST}/init_client/'

try:
    response = requests.post(API, {
        'num_participants': PARTICIPANTS,
        'host': HOST
    })
    assert response.status_code == 200
except Exception as e:
    print(f'Could not connect to {HOST}: {e.__class__.__name__}: {e}')
    exit(-1)

# store returned token, will be used for sending transactions
TOKEN = response.text

################################################################################


# # Enter main loop
while True:
    cmd = input("> ")

    print(cmd)
    if cmd == 'get':
        API = f'{HOST}/get_participants/'
        response = requests.get(API)
        print(response.json())

    if cmd == 'blockchain':
        API = f'{HOST}/get_blockchain/'
        response = requests.get(API)
        print(response.json())

    if cmd == 'balance':
        API = f'{HOST}/get_balance/'
        response = requests.get(API).json()

        for id in response:
            print(id, '\t', response[id]['amount'])

    if cmd.startswith('t'):
        parts = cmd.split()

        API = f'{HOST}/get_balance/'
        response = requests.get(API).json()
        recepient = response[parts[1]]['pubkey']
        amount = parts[2]

        API = f'{HOST}/create_transaction/'
        for _ in range(5):
            response = requests.post(API, {
                'token': TOKEN,
                'recepient': recepient,
                'amount': amount
            })



    if cmd == 'exit':
        exit(-1)