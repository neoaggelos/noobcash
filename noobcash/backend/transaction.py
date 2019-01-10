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
    def validate_transaction(json_string, start_miner=True, check_pending=True):
        '''
        * validate an incoming transaction
        * add to list of transactions
        * start miner if requested/needed

        IMPORTANT NOTE: global state is not altered in case of an invalid transaction

        @return (('added'/'exists'), transaction) OR ('error', None) OR ('hopeful', None)
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

                # assert that it is not using itself as input
                assert t.id not in t.inputs

                # verify that inputs are utxos
                sender_utxos = copy.deepcopy(state.utxos[t.sender])
                budget = 0
                add_to_pending = False
                for txin_id in t.inputs:
                    found = False

                    for utxo in sender_utxos:
                        if utxo['id'] == txin_id and utxo['who'] == t.sender:
                            found = True
                            budget += utxo['amount']
                            sender_utxos.remove(utxo)
                            break

                    if not found and settings.HOPEFUL:
                        # FIXME: only if said input does not appear in a previous transaction?
                        add_to_pending = True
                        break
                    else:
                        assert found

                # hopefully, the missing inputs are transactions that are still on their way
                if add_to_pending:
                    # ehh, an attack would be to keep sending the same transaction over and over
                    if json_string not in state.pending_transactions:
                        state.pending_transactions.append(json_string)

                    return 'hopeful', None

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

                # update utxos, this is final
                sender_utxos.append(t.outputs[0])
                state.utxos[t.sender] = sender_utxos
                state.utxos[t.recepient].append(t.outputs[1])
                state.transactions.append(t)

                # pending txs have been checked, this will not crash
                if settings.HOPEFUL and check_pending:
                    Transaction.replay_pending_transactions([t.id], t.inputs)

                # append to transactions, and start miner if needed
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
            assert recepient != sender

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

    @staticmethod
    def replay_pending_transactions(validated_txin_ids=[], used_inputs=[]):
        try:
            pending_to_remove = []
            pending_to_check = []
            for pending_tx_json in state.pending_transactions:
                pending_tx_dict = json.loads(pending_tx_json)
                for pending_txin_id in pending_tx_dict['inputs']:
                    # if any of its inputs were used, we will drop it
                    if pending_txin_id in used_inputs:
                        pending_to_remove.append(pending_tx_json)
                        break

                    # if new transaction is its input, we will try validating it
                    elif pending_txin_id in validated_txin_ids:
                        pending_to_check.append(pending_tx_json)
                        break

            # remove invalid, this is final.
            for tx_json in pending_to_remove:
                state.pending_transactions.remove(tx_json)

            # for the (possibly many, in case of double spending) canditates
            for tx_json in pending_to_check:
                PENDING_TRANSACTIONS_BACKUP = copy.deepcopy(state.pending_transactions)

                state.pending_transactions.remove(tx_json)
                res, tx = Transaction.validate_transaction(tx_json, start_miner=False)
                if res == 'added':
                    # NOTE: adding means that all others will be removed in the recursion
                    # we don't have to do anything else here
                    break
                elif res == 'hopeful':
                    # this may happen if more than one inputs are missing
                    # re-adding would not work well, we want to maintain order
                    state.pending_transactions = PENDING_TRANSACTIONS_BACKUP
                else:
                    # this should never happen
                    print('RANDOM LOL')

        except Exception as e:
            print(f'Transaction.check_pending_transactions: {e.__class__.__name__}: {e}')