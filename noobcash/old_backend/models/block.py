# block.py

import datetime
import json

from noobcash.backend.settings import BLOCK_CAPACITY, DIFFICULTY
from django.db import models

from Crypto.Hash import SHA384

from noobcash.backend.models import Transaction
from noobcash.backend import miner

################################################################################

class Block(models.Model):
    index = models.IntegerField(null=True)
    timestamp = models.DateTimeField(null=False, default=datetime.datetime.now)
    transactions = models.TextField(null=False) # JSON of [transaction_1, ...]
    nonce = models.IntegerField(null=False)
    current_hash = models.TextField(null=False)
    previous_hash = models.TextField(null=False)


    # what we send
    def dump_sendable(self):
        return json.dumps(dict(
            timestamp=self.timestamp,
            transactions=self.transactions,
            nonce=self.nonce,
            current_hash=self.current_hash,
            previous_hash=self.previous_hash
        ), sort_keys=True)


    # used to calculate hash
    def dump(self):
        return json.dumps(dict(
            transactions=self.transactions,
            nonce=self.nonce
        ), sort_keys=True)


    # calculate hash
    def calculate_hash(self):
        return SHA384.new(self.dump())


    @staticmethod
    def validate_block(block_json_string):

        miner.stop_if_running()

        try:
            next_id = Block.objects.all().count()
            prev_block = Block.objects.get(index=next_id-1)

            block = Block(**json.loads(block_json_string), index=next_id)
            transactions = json.loads(block.transactions)

            if block.current_hash[0:DIFFICULTY] != ('0'*DIFFICULTY):
                return 'error', None
            if block.calculate_hash() != block.current_hash:
                return 'error', None
            if len(block.transactions) != BLOCK_CAPACITY:
                return 'error', None

            tx_list = []
            for tx_json_string in transactions:
                tx_dict = json.loads(tx_json_string)

                # ensures all transactions were not in a previous block
                tx = Transaction.objects.get(hash=tx_dict['hash'], used=False)
                tx.used = True
                tx_list.append(tx)

            if block.previous_hash != prev_block.current_hash:
                # TODO: do consensus crap
                # THIS IS GONNA BE SOME RIDE WOOOOO-HOOO
                return 'consensus', None

            # only update if all transactions were ok
            assert len(transactions) == len(tx_list)

            # Below this line, block is legit, update state
            for tx in tx_list:
                tx.save()

            if Transaction.objects.filter(used=False) >= BLOCK_CAPACITY:
                miner.start_on_background()

            # block is go
            return block
        except Exception as e:
            print(f'Block.validate_block: {e.__class__.__name__}: {e}')
            return None

    @staticmethod
    def create_block()