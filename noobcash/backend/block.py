# block.py

import copy
import json
import datetime

from Crypto.Hash import SHA384

from noobcash.backend import settings, miner, state
from noobcash.backend.transaction import Transaction

################################################################################

class Block(object):
    '''
    A block object has the following fields

    'transactions': list of transactions in the block [json_string_1, json_string_2, ...]
    'nonce': farmed nonce

    'current_hash': hash of the above
    'previous_hash': hash of previous block

    'index': index of this block in the chain
    'timestamp': time of block creation
    '''

    def __init__(self, transactions, nonce, current_hash, previous_hash, index, timestamp=None):
        '''dummy create new block'''
        self.transactions = transactions
        self.nonce = nonce
        self.current_hash = current_hash
        self.previous_hash = previous_hash

        self.index = index
        self.timestamp = timestamp
        if timestamp is None:
            self.timestamp = str(datetime.datetime.now())


    def __eq__(self, o):
        '''equality check'''
        if not isinstance(o, Block):
            return False

        return (self.transactions == o.transactions
            and self.nonce == o.nonce
            and self.previous_hash == o.previous_hash
            and self.current_hash == o.current_hash)


    def dump_sendable(self):
        ''' sendable json string '''
        return json.dumps(dict(
            timestamp=self.timestamp,
            transactions=self.transactions,
            nonce=self.nonce,
            current_hash=self.current_hash,
            previous_hash=self.previous_hash
        ), sort_keys=True)

    def dict(self):
        return dict(
            timestamp=self.timestamp,
            transactions=self.transactions,
            nonce=self.nonce,
            current_hash=self.current_hash,
            previous_hash=self.previous_hash
        )

    def dump(self):
        ''' used for calculating hash '''
        return json.dumps(dict(
            transactions=self.transactions,
            nonce=self.nonce
        ), sort_keys=True)


    def calculate_hash(self):
        ''' dont calculate hash '''
        return SHA384.new(self.dump().encode())


    @staticmethod
    def validate_block(json_string):
        '''
        validate incoming block.

        @return
        * 'οκ'        <-- everything went ok, block was added in the blockchain (along with any new transactions)
        * 'dropped'   <-- block is not increasing the chain length, so it was dismissed (***)
        * 'error'     <-- error occured, block dismissed
        * 'consensus' <-- branch detected, we need to ask the other nodes

        [***]: if the chain length implied by the received block is smaller, then we may safely ignore it
               if the chain length is the same, we may choose whichever chain we want at random, so we choose our own
               if the chain length is bigger, we should receive another block soon.

               --> in any case, we can safely drop this block, even if it is valid
        '''
        # acquire locks for everything
        with state.lock:
            try:
                # save state, in order to properly restore in case of a bad block
                TRANSACTIONS_BACKUP = copy.deepcopy(state.transactions)
                UTXOS_BACKUP = copy.deepcopy(state.utxos)
                BLOCKCHAIN_BACKUP = copy.deepcopy(state.blockchain)
                VALID_UTXOS_BACKUP = copy.deepcopy(state.valid_utxos)

                prev_block = state.blockchain[-1]
                block = Block(**json.loads(json_string), index=prev_block.index+1)

                if len(block.transactions) != settings.BLOCK_CAPACITY:
                    raise Exception('invalid block capacity')
                if block.calculate_hash().hexdigest() != block.current_hash:
                    raise Exception('invalid block hash')
                if not block.current_hash.startswith('0' * settings.DIFFICULTY):
                    raise Exception('invalid proof of work')

                if block.previous_hash == prev_block.current_hash:
                    # HO-HO-HO, OUR LUCKY DAY

                    # start from utxos as of last block
                    state.utxos = copy.deepcopy(state.valid_utxos)
                    state.transactions = []

                    for tx_json in block.transactions:
                        # this will make sure transactions are valid, and it will update utxos as well
                        status, block_tx = Transaction.validate_transaction(tx_json)
                        if status != 'added':
                            raise Exception(f'invalid block transaction: validation returned {status}')

                        # remove transaction after validating
                        state.transactions.remove(block_tx)

                    # append block, update valid utxos
                    state.blockchain.append(block)
                    state.valid_utxos = copy.deepcopy(state.utxos)

                    # update sendable blockchain (without genesis block)
                    with state.blockchain_public_lock:
                        state.blockchain_public = [b.dump_sendable() for b in state.blockchain[1:]]

                    # re-play the other transactions that are still waiting to enter a block
                    # If any one fails, sender is fraudulent, but oh well
                    for tx in TRANSACTIONS_BACKUP:
                        tx_json = tx.dump_sendable()
                        if tx_json not in block.transactions:
                            status, tx = Transaction.validate_transaction(tx_json)

                    return 'ok'

                else:
                    for existing_block in state.blockchain[:-1]:
                        if existing_block.current_hash == block.previous_hash:
                            # the new block's parent is a previous block. so this new block
                            # creates a different chain, one whose length is not larger
                            # than the one we have. we may choose whichever chain we want,
                            # we choose our own for simplicity
                            return 'dropped'

                    # unknown block, ask other nodes
                    return 'consensus'

            except Exception as e:
                # restore state and return
                state.transactions = TRANSACTIONS_BACKUP
                state.blockchain = BLOCKCHAIN_BACKUP
                state.utxos = UTXOS_BACKUP
                state.valid_utxos = VALID_UTXOS_BACKUP

                print(f'Block.validate_block: {e.__class__.__name__}: {e}')
                return 'error'


    @staticmethod
    def create_block(transactions, nonce, sha):
        '''
        the miner found `nonce` for the list of `transactions`.
        create a block, append to our own blockchain and return it
        '''
        try:
            # lock and go
            with state.lock:
                TRANSACTIONS_BACKUP = copy.deepcopy(state.transactions)
                UTXOS_BACKUP = copy.deepcopy(state.utxos)
                VALID_UTXOS_BACKUP = copy.deepcopy(state.valid_utxos)

                block = Block(
                    transactions=copy.deepcopy(transactions),
                    nonce=nonce,
                    current_hash=sha,
                    previous_hash=state.blockchain[-1].current_hash,
                    index=len(state.blockchain)
                )

                if len(block.transactions) != settings.BLOCK_CAPACITY:
                    raise Exception('invalid block capacity')
                if block.current_hash != block.calculate_hash().hexdigest():
                    raise Exception('invalid block hash')
                if not block.current_hash.startswith('0' * settings.DIFFICULTY):
                    raise Exception('invalid proof of work')

                # start from utxos of last block
                state.utxos = copy.deepcopy(state.valid_utxos)
                state.transactions = []

                for tx_json_string in transactions:
                    status, t = Transaction.validate_transaction(tx_json_string)
                    if status != 'added':
                        raise Exception('transaction already exists')

                # remove them again
                state.transactions = []

                # append to blockchain, update valid utxos
                state.blockchain.append(block)
                state.valid_utxos = copy.deepcopy(state.utxos)

                # update sendable blockchain (without genesis block)
                with state.blockchain_public_lock:
                    state.blockchain_public = [b.dump_sendable() for b in state.blockchain[1:]]

                # re-play transactions waiting to enter a block
                for tx in TRANSACTIONS_BACKUP:
                    tx_json_string = tx.dump_sendable()
                    if tx_json_string not in transactions:
                        status, t = Transaction.validate_transaction(tx_json_string)

                # plus one
                state.num_blocks_created += 1

                return block

        except Exception as e:
            state.transactions = TRANSACTIONS_BACKUP
            state.utxos = UTXOS_BACKUP
            state.valid_utxos = VALID_UTXOS_BACKUP
            print(f'Block.create_block: {e.__class__.__name__}: {e}')
            return None


    @staticmethod
    def create_genesis_block(count):
        '''
        creates genesis block (the only unvalidated block for the chain)
        '''
        try:

            if not Transaction.create_genesis_transaction(count):
                raise Exception('could not create genesis transaction')

            with state.lock:
                block = Block(
                    transactions=[tx.dump_sendable() for tx in state.transactions],
                    nonce=0,
                    previous_hash='1',
                    index=0,
                    current_hash='placeholder'
                )

                block.current_hash = block.calculate_hash().hexdigest()

                state.blockchain = [block]
                state.transactions = []
                state.valid_utxos = copy.deepcopy(state.utxos)

                state.genesis_block = Block(**json.loads(block.dump_sendable()), index=0)
                state.genesis_utxos = copy.deepcopy(state.utxos)

            return True

        except Exception as e:
            print(f'Block.create_genesis_block: {e.__class__.__name__}: {e}')
            return False
