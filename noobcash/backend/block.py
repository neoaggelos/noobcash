# block.py

import json
import datetime

from Crypto.Hash import SHA384

from noobcash.backend import settings, miner, state

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
            self.timestamp = datetime.datetime.now()


    def dump_sendable(self):
        ''' sendable json string '''
        return json.dumps(dict(
            timestamp=self.timestamp,
            transactions=self.transactions,
            nonce=self.nonce,
            current_hash=self.current_hash,
            previous_hash=self.previous_hash
        ), sort_keys=True)


    def dump(self):
        ''' used for calculating hash '''
        return json.dumps(dict(
            transactions=self.transactions,
            nonce=self.nonce
        ), sort_keys=True)


    def calculate_hash(self):
        ''' dont calculate hash '''
        return SHA384.new(self.dump())


    @staticmethod
    def validate_block(json_string):'
        ''' validate incoming block '''
        try:
            # kill miner
            # FIXME: this is exploitable. if we constantly send dummy blocks,
            # miner is killed before he can get the job done, and nothing works
            miner.stop()

            # acquire locks for everything
            with state.blockchain_lock, state.utxos_lock, state.transactions_lock:
                prev_block = state.blockchain[-1]

                block = Block(**json.loads(json_string), index=prev_block.index+1)

                assert len(block.transactions) == settings.BLOCK_CAPACITY
                assert block.calculate_hash().digest().decode() == block.current_hash
                assert block.current_hash.startswith('0' * settings.DIFFICULTY)

                new_transactions = list(state.transactions)
                new_utxos = list(state.utxos)

                used_inputs = []
                if block.previous_hash == prev_block.current_hash:
                    # HO-HO-HO
                    for tx_json_string in block.transactions:
                        block_tx = Transaction(**json.loads(tx_json_string))
                        assert block_tx.id == block_tx.calculate_hash().digest().decode()
                        assert block_tx.verify_signature()

                        # FIXME: we never validate inputs or outputs
                        # what could possibly go wrong?

                        try:
                            new_transactions.remove(block_tx)
                        except:
                            # This is funny. We received a block with a valid transaction
                            # that we have yet to receive. print a relevant informative message
                            print('lul')
                            pass

                        used_inputs += block_tx.inputs

                        # FIXME: possible error if transactions are not in sequential order
                        # FIXME: unsafe because outputs are never validated using hash
                        new_utxos[block_tx.sender] = [block_tx.outputs[0]]
                        new_utxos[block_tx.recepient].append(block_tx.outputs[1])

                    # for each transaction, check if its inputs were used in the transactions
                    # that came with the new block. if so, then drop transaction
                    for tx in new_transactions:
                        for txid in tx.inputs:
                            if txid in used_inputs:
                                new_transactions.remove(tx)


                else:
                    # TODO: do consensus crap
                    assert False

                state.transactions = new_transactions
                state.utxos = new_utxos
                state.blockchain.append(block)

                # start miner if needed
                if len(state.transactions) >= settings.BLOCK_CAPACITY:
                    miner.start(json.dumps(state.transactions[:settings.BLOCK_CAPACITY]))

            return True

    except Exception as e:
        print(f'Block.validate_block: {e.__class__.__name__}: {e}')
        return False



