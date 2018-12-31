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
def _start(block):
    try:
        proc = Popen(['python', __file__, block])
        state.miner_pid = proc.pid

    except Exception as e:
        print(f'miner.start: {e.__class__.__name__}: {e}')


def start(block):
    try:
        os.kill(state.miner_pid, 0)

    except:
        _start(block)


def stop():
    try:
        os.kill(state.miner_pid, SIGTERM)
    except OSError as e:
        if e.errno != os.errno.ESRCH:
            print(f'miner.stop: {e.errno}: {e}')
    except Exception as e:
        print(f'miner.stop: {e.__class__.__name__}: {e}')


###############################################################################

def announce_nonce(dad, block_json_string, block_hash, nonce):
    # NOTE: miner is a fragile process, it may get killed at any point
    # dont start sending blocks around, if we die midway its gonna get bad
    # just tell dad and exit, let him worry about sending crap around
    api = f'{dad}/miner_finished'

    response = requests.post(api, {
        'block_json_string': block_json_string,
        'block_hash': block_hash,
        'nonce': nonce
    })

    if response.status_code != 200:
        print(f'miner.announce_nonce: request failed: {response.text}')

    # FIXME: check if new block is ready to mine?
    exit(0)


def do_mine(json_string):
    server = None
    for p in state.participants:
        if p['id'] == state.participant_id:
            server = p['server']

    if server is None:
        print(f'Mommy, where am I?', p['id'])

    # wtf
    transactions = json.loads(json_string)
    if len(transactions) < settings.BLOCK_CAPACITY:
        print('Dont shit on me, Rogers, did you know?')

    # create base
    base = {}
    base['transactions'] = [tx.dump_sendable() for tx in transactions]

    # try coming up with random numbers until hash is good
    seed()
    while True:
        nonce = randint(0, 4294967295)  # compute a random 32-bit value
        base['nonce'] = nonce

        base_json_string = json.dumps(base, sort_keys=True)
        hash = SHA384.new(base_json_string).digest().decode()

        if hashed.startswith('0' * settings.DIFFICULTY):
            announce_nonce(dad, base_json_string, hash, nonce)
            exit(0)


################################################################################

if __name__ == '__main__':
    do_mine(sys.argv[1])