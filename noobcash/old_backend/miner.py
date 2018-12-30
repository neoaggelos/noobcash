import os, django, sys
import json
import datetime
import requests

from random import seed, randint
from subprocess import Popen
from signal import SIGTERM
from Crypto.Hash import SHA384

from noobcash.backend.models import NodeInfo, Transaction, Node, Block, KeyPair
from noobcash.backend import settings


################################################################################

# Set up django
BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(BASE)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noobcash.settings')
django.setup()

################################################################################

# dumb starter
def start(block):
    try:
        node = NodeInfo.objects.get()
        proc = Popen(['python', __file__, block])
        node.miner_pid = proc.pid
        node.save()

    except Exception as e:
        print(f'start_miner: {e.__class__.__name__}: {e}')


def start_if_not_running(block):
    try:
        node = NodeInfo.objects.get()
        os.kill(node.miner_pid, 0)

    except:
        start(block)


def stop():
    try:
        node = NodeInfo.objects.get()
        os.kill(node.miner_pid, SIGTERM)
    except OSError as e:
        if e.errno != os.errno.ESRCH:
            print(f'miner.stop: {e.errno}: {e}')
    except Exception as e:
        print(f'miner.stop: {e.errno}: {e}')


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

    if response.status_code == 200:
        exit(0)

    print(f'miner.announce_nonce: request failed: {response.text}')


def do_mine():
    dad = Node.objects.get(pubkey=KeyPair.get_public_key()).server

    transactions = Transaction.objects.filter(used=False)
    transactions = transactions.limit(settings.BLOCK_CAPACITY)
    transactions = transactions.order_by('id')

    # wtf
    if transactions.count() < settings.BLOCK_CAPACITY:
        exit(-1)

    # create base
    tx_dicts = [tx.dump() for tx in transactions]

    # try coming up with random numbers until hash is good
    seed()
    base = {}
    base['transactions'] = json.dumps(tx_dicts)
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
    do_mine()