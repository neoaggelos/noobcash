# transaction.py

import json
from Crypto.Hash import SHA384
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5

from noobcash.backend import state, miner, settings

class Transaction(object):
    '''
    a transaction object has the following fields

    'sender': pubkey of sender
    'recepient': pubkey of recepient
    'amount': transaction amount
    'inputs': list of transaction ids used as inputs

    'id': transaction id (hash of above info)

    'outputs': utxos for sender and recepient [{transaction_id, who, amount}]
    'signature': hash signed by sender private key
    '''

    def __init__(self, sender, recepient, amount, inputs, id=None, signature=None, outputs=[]):
        '''init'''
        self.sender = sender
        self.recepient = recepient
        self.amount = amount
        self.inputs = inputs

        self.id = id
        self.signature = signature
        self.outputs = outputs


    def dump_sendable(self):
        '''convert to sendable json string'''
        return json.dumps(dict(
            sender=self.sender,
            recepient=self.recepient,
            amount=self.amount,
            inputs=self.inputs,
            outputs=self.outputs,
            id=self.id,
            signature=self.signature
        ), sort_keys=True)


    def dump(self):
        '''convert to json string to calculate hash'''
        return json.dumps(dict(
            sender=self.sender,
            recepient=self.recepient,
            amount=self.amount,
            inputs=self.inputs
            ), sort_keys=True)


    def calculate_hash(self):
        '''calculate hash of transaction'''
        return SHA384.new(self.dump())


    def sign(self):
        '''sign a transaction using our private key'''
        hash_obj = hash_transaction(self)

        rsa_key = RSA.importKey(state.privkey)
        signer = PKCS1_v1_5.new(rsa_key)

        self.id = hash_obj.digest().decode()
        self.signature = signer.sign(hash_obj)


    def verify_signature(self):
        '''verify the signature of an incoming transaction'''
        try:
            rsa_key = RSA.importKey(self.sender.encode())
            verifier = PKCS1_v1_5.new(rsa_key)

            hash_obj = self.calculate_hash()
            return verifier.verify(hash_obj, self.signature)
        except Exception as e:
            print(f'verify_signature: {e.__class__.__name__}: {e}')
            return False


    @staticmethod
    def validate_transaction(json_string):
        '''validate an incoming transaction, add to list of transactions and start miner if needed'''
        try:
            t = Transaction(**json.loads(json_string))
            assert t.sender != t.recepient
            assert t.sender in state.participants
            assert t.recepient in state.participants

            assert isinstance(t.id, str)
            assert isinstance(t.signature, str)
            assert t.amount > 0
            assert t.id == t.calculate_hash().digest().decode()

            # verify signature
            assert t.verify_signature()

            # verify that transaction inputs are unique
            assert len(set(inputs)) == len(inputs)

            # verify that inputs are utxos
            with state.utxos_lock:
                sender_utxos = list(state.utxos[t.sender])
                sender_initial_money = 0
                for txin_id in t.inputs:
                    found = False

                    for utxo in sender_utxos:
                        if utxo['id'] == txin_id and utxo['who'] == t.sender:
                            found = True
                            sender_initial_money += utxo['amount']
                            sender_utxos.remove(utxo)
                            break

                    assert found

                # verify sender has enough cash
                assert not (amount < sender_initial_money)

                # create outputs
                t.outputs = [{
                    'id': t.id,
                    'who': t.sender,
                    'amount': sender_initial_money - t.amount
                }, {
                    'id': t.id,
                    'who': t.recepient,
                    'amount': t.amount
                }]

                # update utxos
                state.utxos[t.sender] = [t.outputs[0]]
                state.utxos[t.recepient].append(t.outputs[1])

                with state.transactions_lock:
                    state.transactions.append(t)

                    if len(state.transactions) >= settings.BLOCK_CAPACITY:
                        transactions = state.transactions[:settings.BLOCK_CAPACITY]
                        miner.start_if_not_running(transactions)

            return True

        except Exception as e:
            print(f'Transaction.validate_transaction: {e.__class__.__name__}: {e}')
            return False


    @staticmethod
    def create_transaction(recepient, amount):
        try:
            sender = state.pubkey

            assert recepient in state.participants

            with state.utxos_lock:
                sender_utxos = list(state.utxos[sender])
                recepient_utxos = list(state.utxos[recepient])

                inputs = [tx['id'] for tx in sender_utxos]
                budget = sum(tx['amount'] for tx in sender_utxos if sender_utxos['who'] == sender)

                assert not amount < budget

                t = Transaction(sender=sender, recepient=recepient, amount=amount, inputs=inputs)
                t.sign()

                t.outputs = [{
                    'id': t.id,
                    'who': t.sender,
                    'amount': budget - amount
                }, {
                    'id': t.id,
                    'who': t.recepient,
                    'amount': amount
                }]

                state.utxos[sender] = [t.outputs[0]]
                state.utxos[recepient].append(t.outputs[1])

                with state.transactions_lock:
                    state.transactions.append(t)

                    if len(state.transactions) >= settings.BLOCK_CAPACITY:
                        transactions = state.transactions[:settings.BLOCK_CAPACITY]
                        miner.start(transactions)
