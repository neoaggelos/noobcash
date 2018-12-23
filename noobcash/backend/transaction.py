# transaction.py

import Crypto

# A single transaction
class Transaction:
    def __init__(self, sender, receiver, amount):
        self.sender_address = sender
        self.receiver_address = receiver
        self.amount = amount

        # TODO: validate above and set these
        self.transaction_inputs = []
        self.transaction_outputs = []
        self.signature = None

    # TODO