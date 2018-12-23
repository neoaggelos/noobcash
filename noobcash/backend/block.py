# block.py

from .noobcash_settings import BLOCK_CAPACITY

# A fundemental block, contains a list of transactions
class Block:
    def __init__(self, previous_hash, index):
        self.index = index
        self.transactions = []
        self.previous_hash = previous_hash

        # random init
        self.nonce = None
        self.timestamp = None
        self.current_hash = None

    # TODO
