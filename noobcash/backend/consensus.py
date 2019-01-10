from noobcash.backend import state
from noobcash.backend.block import Block

import copy
import requests

def validate_chain(blockchain, pending):
    '''
    Check if `blockchain` is a valid chain of blocks.
    Also update `transactions` and `utxos` for it.

    @return True if valid, False otherwise
    '''
    with state.lock:
        # restart from genesis block
        state.blockchain = copy.deepcopy(state.genesis_block)
        state.utxos = copy.deepcopy(state.genesis_utxos)

        # pending transactions
        # FIXME: this could be done just before the last block, for faster
        state.transactions = copy.deepcopy(pending)

        # for the chain to be valid, we have to be able to append each block
        # without errors.
        for block in blockchain:
            # `Block.validate_block()` will also update any pending transactions
            # with conflicting inputs
            res = Block.validate_block(block, start_miner=False)

            if res != 'ok':
                return False

        return True

def consensus():
    # we don't want someone else to interfere while asking for consensus
    # lock up the darkness
    with state.lock:
        # keep backup
        MAX_BLOCKCHAIN = copy.deepcopy(state.blockchain)
        MAX_TRANSACTIONS = copy.deepcopy(state.transactions)
        MAX_UTXOS = copy.deepcopy(state.utxos)
        MAX_LENGTH = len(MAX_BLOCKCHAIN)
        TRANSACTIONS_BACKUP = copy.deepcopy(state.transactions)

        for participant in state.participants.values():
            # skip self
            if participant['id'] == state.participant_id:
                continue

            try:
                pid = participant['id']
                host = participant['host']
                api = f'{host}/get_blockchain/'

                response = requests.get(api)
                assert response.status_code == 200

                received_blockchain = response.json()['blockchain']

                # NOTE: we received the blockchain WITHOUT the genesis block. This means
                # that the received chain size is actually `len(received_blockchain) + 1`
                # We want to keep chains with length > MAX_LENGTH
                if len(received_blockchain) < MAX_LENGTH:
                    continue

                assert validate_chain(received_blockchain, TRANSACTIONS_BACKUP)

                # if chain is valid, update
                MAX_BLOCKCHAIN = copy.deepcopy(state.blockchain)
                MAX_TRANSACTIONS = copy.deepcopy(state.transactions)
                MAX_UTXOS = copy.deepcopy(state.utxos)
                MAX_LENGTH = len(MAX_BLOCKCHAIN)

            except Exception as e:
                print(f'consensus.{pid}: {e.__class__.__name__}: {e}')

        # update with best blockchain found
        state.blockchain = MAX_BLOCKCHAIN
        state.transactions = MAX_TRANSACTIONS
        state.utxos = MAX_UTXOS

