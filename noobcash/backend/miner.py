import os, django, sys
import json
import datetime
import requests

from random import seed, randint
from subprocess import Popen
from signal import SIGTERM
from Crypto.Hash import SHA384
################################################################################

# Set up django
BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(BASE)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noobcash.settings')
django.setup()

################################################################################

from noobcash.backend import settings, state

# dumb starter
def _start(transactions_list):
    try:
        proc = Popen(['python', __file__, transactions_list])
        state.miner_pid = proc.pid

    except Exception as e:
        print(f'miner.start: {e.__class__.__name__}: {e}')


def start(transactions_list):
    try:
        os.kill(state.miner_pid, 0)

    except:
        _start(transactions_list)


def stop():
    try:
        os.kill(state.miner_pid, SIGTERM)
    except OSError as e:
        if e.errno != os.errno.ESRCH:
            print(f'miner.stop: {e.errno}: {e}')
    except Exception as e:
        print(f'miner.stop: {e.__class__.__name__}: {e}')


###############################################################################

def announce_nonce(dad, transactions, nonce, sha):
    # NOTE: miner is a fragile process, it may get killed at any point
    # dont start sending blocks around, if we die midway its gonna get bad
    # just tell dad and exit, let him worry about sending crap around
    api = f'{dad}/miner_finished'

    response = requests.post(api, {
        'transactions': transactions,
        'sha': sha,
        'nonce': nonce
    }, wait)

    if response.status_code != 200:
        print(f'miner.announce_nonce: request failed: {response.text}')

    # FIXME: if we need to mine another block
    exit(0)


def do_mine(json_string):
    host = None
    for p in state.participants:
        if p['id'] == state.participant_id:
            host = p['host']

    if host is None:
        print(f'Mommy, where am I?', p['id'])
        exit(-1)

    # wtf
    transactions = json.loads(json_string)
    if len(transactions) != settings.BLOCK_CAPACITY:
        print('Dont shit on me, Rogers, did you know?')
        exit(-1)

    # create base
    base = {}
    base['transactions'] = transactions

    # try coming up with random numbers until hash is good
    seed()
    nonce = randint(0, 4294967295)  # compute a random 32-bit value
    while True:
        base['nonce'] = nonce

        base_json_string = json.dumps(base, sort_keys=True)
        sha = SHA384.new(base_json_string).digest().decode()

        if sha.startswith('0' * settings.DIFFICULTY):
            announce_nonce(host, transactions, sha, nonce)
            exit(0)

        # DISCUSS
        # use next value
        nonce = (nonce + 1) % 4294967295
        # use random value
        nonce = randint(0, 4294967295)  # compute a random 32-bit value


################################################################################

if __name__ == '__main__':
    do_mine(sys.argv[1])
