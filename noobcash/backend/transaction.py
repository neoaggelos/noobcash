# transaction.py

import copy
import json

from Crypto.Hash import SHA384
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
import base64

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

    def __init__(self, sender, recepient, amount, inputs, id=None, signature=None):
        '''init'''
        self.sender = sender
        self.recepient = recepient
        self.amount = amount
        self.inputs = inputs

        self.id = id
        self.signature = signature
        self.outputs = []


    def __eq__(self, o):
        ''' equality check, needed for comparing when removing/adding to list '''
        if not isinstance(o, Transaction):
            return False

        return self.dump_sendable() == o.dump_sendable()


    def dump_sendable(self):
        '''convert to sendable json string'''
        return json.dumps(dict(
            sender=self.sender,
            recepient=self.recepient,
            amount=self.amount,
            inputs=self.inputs,
            id=self.id,
            signature=self.signature
        ), sort_keys=True)

    def dict(self):
        '''convert to dict'''
        return dict(
            sender=self.sender,
            recepient=self.recepient,
            amount=self.amount,
            inputs=self.inputs,
            id=self.id,
            signature=self.signature
        )


    def dump(self):
        '''convert to json string to calculate hash'''
        return json.dumps(dict(
            sender=self.sender,
            recepient=self.recepient,
            amount=self.amount,
            inputs=self.inputs,
            ), sort_keys=True)


    def calculate_hash(self):
        '''calculate hash of transaction'''
        return SHA384.new(self.dump().encode())


    def sign(self):
        '''sign a transaction using our private key'''
        hash_obj = self.calculate_hash()

        rsa_key = RSA.importKey(state.privkey)
        signer = PKCS1_v1_5.new(rsa_key)

        self.id = hash_obj.hexdigest()
        self.signature = base64.b64encode(signer.sign(hash_obj)).decode()


    def verify_signature(self):
        '''verify the signature of an incoming transaction'''
        try:
            rsa_key = RSA.importKey(self.sender.encode())
            verifier = PKCS1_v1_5.new(rsa_key)

            hash_obj = self.calculate_hash()
            return verifier.verify(hash_obj, base64.b64decode(self.signature))
        except Exception as e:
            print(f'verify_signature: {e.__class__.__name__}: {e}')
            return False


    @staticmethod
    def validate_transaction(json_string, start_miner=True):
        '''
        * validate an incoming transaction
        * add to list of transactions
        * start miner if requested/needed

        @return (('added'/'exists'), transaction) OR ('error', None)
        '''
        try:
            t = Transaction(**json.loads(json_string))

            with state.lock:
                if t in state.transactions:
                    return 'exists', t

                assert t.sender != t.recepient
                assert t.sender in state.participants
                assert t.recepient in state.participants

                assert isinstance(t.id, str)
                assert isinstance(t.signature, str)
                assert t.amount > 0
                assert t.id == t.calculate_hash().hexdigest()

                # verify signature
                assert t.verify_signature()

                # verify that transaction inputs are unique
                assert len(set(t.inputs)) == len(t.inputs)

                # verify that inputs are utxos
                sender_utxos = copy.deepcopy(state.utxos[t.sender])
                budget = 0
                for txin_id in t.inputs:
                    found = False

                    for utxo in sender_utxos:
                        if utxo['id'] == txin_id and utxo['who'] == t.sender:
                            found = True
                            budget += utxo['amount']
                            sender_utxos.remove(utxo)
                            break

                    assert found

                # verify money is enough
                assert budget >= t.amount

                # create outputs
                t.outputs = [{
                    'id': t.id,
                    'who': t.sender,
                    'amount': budget - t.amount
                }, {
                    'id': t.id,
                    'who': t.recepient,
                    'amount': t.amount
                }]

                # update utxos
                sender_utxos.append(t.outputs[0])
                state.utxos[t.sender] = sender_utxos
                state.utxos[t.recepient].append(t.outputs[1])

                # append to transactions, and start miner if needed
                state.transactions.append(t)
                if len(state.transactions) >= settings.BLOCK_CAPACITY and start_miner:
                    miner.start()

            return 'added', t

        except Exception as e:
            print(f'Transaction.validate_transaction: {e.__class__.__name__}: {e}')
            # raise e
            return 'error', None


    @staticmethod
    def create_transaction(recepient, amount, start_miner=True):
        '''
        create a new transaction that sends `amount` nbc to `recepient`
        @return The transaction object, or None in case of error
        '''
        try:
            sender = state.pubkey

            assert recepient in state.participants
            amount = float(amount)

            with state.lock:
                sender_utxos = copy.deepcopy(state.utxos[sender])
                recepient_utxos = copy.deepcopy(state.utxos[recepient])

                inputs = [tx['id'] for tx in sender_utxos]
                budget = sum(tx['amount'] for tx in sender_utxos if tx['who'] == sender)

                assert budget >= amount

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

                state.transactions.append(t)

                if len(state.transactions) >= settings.BLOCK_CAPACITY and start_miner:
                    miner.start()

            return t

        except Exception as e:
            print(f'Transaction.create_transaction: {e.__class__.__name__}: {e}')
            raise Exception() from e
            return None


    @staticmethod
    def create_genesis_transaction(num_participants):
        '''the one transaction to rule them all'''
        try:
            t = Transaction(
                sender=state.pubkey,
                recepient=state.pubkey,
                amount=100*num_participants,
                inputs=[]
            )
            t.sign()

            t.outputs = [{
                'id': t.id,
                'who': t.sender,
                'amount': t.amount
            }]

            with state.lock:
                state.utxos[state.pubkey] = [t.outputs[0]]
                state.transactions.append(t)

            return True
        except Exception as e:
            print(f'Transaction.create_genesis_transaction: {e.__class__.__name__}: {e}')
            return False