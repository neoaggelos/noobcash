# transaction.py

import json
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA384

from django.db import models
from .keys import KeyPair
from .wallet import Wallet

#################################################################

class Transaction(models.Model):
    # fields
    sender = models.TextField(null=False)
    recepient = models.TextField(null=False)
    amount = models.DecimalField(null=False, decimal_places=2, max_digits=10)

    inputs = models.TextField(null=False) # jsonstring([hash1, hash2, ..., hashN])
    outputs = models.TextField(null=True) # jsonstring([{'hash', 'who', 'amount'}]), for sender and recepient

    hash = models.TextField(null=True)
    signature = models.TextField(null=True)

    used = models.BooleanField(null=False, default=False) # whether transaction is in a block



    # when we send, we also send signature
    def dump_sendable(self):
        return json.dumps(dict(
            sender=self.sender,
            recepient=self.recepient,
            amount=self.amount,
            inputs=self.inputs,
            hash=self.hash,
            signature=self.signature
            ), sort_keys=True)


    # convert sender/receiver/amount/inputs to json string
    def dump(self):
        return json.dumps(dict(
            sender=self.sender,
            recepient=self.recepient,
            amount=self.amount,
            inputs=self.inputs
        ), sort_keys=True)


    # parse json string
    @staticmethod
    def parse_json(json_string):
        trans = json.loads(json_string)
        return Transaction(**trans)



    # calculate hash of transaction dump
    # @return: hash object
    def calculate_hash(self):
        return SHA384.new(self.dump())


    # sign a transaction
    def sign(self):
        hash_obj = self.calculate_hash()

        rsa_key = RSA.importKey(KeyPair.get_private_key())
        signer = PKCS1_v1_5.new(rsa_key)

        self.hash = hash_obj.digest().decode()
        self.signature = signer.sign(hash_obj)


    # verify signature of incoming transaction
    def verify_signature(self):
        try:
            rsa_key = RSA.importKey(self.sender.encode())
            verifier = PKCS1_v1_5.new(rsa_key)

            hash_obj = self.calculate_hash()
            return verifier.verify(hash_obj, self.signature)
        except Exception as e:
            print(f'verify_signature: {e.__class__.__name__}: {e}')
            return False


    # validate incoming transaction
    @staticmethod
    def validate_transaction(json_string):
        try:
            t = Transaction.parse_json(json_string)
            assert t.sender != t.recepient
            assert t.hash is not None
            assert t.signature is not None

            if not t.verify_signature():
                return False

            # FIXME: verify hash from message?

            # verify that input transactions are legit
            inputs = json.loads(τ.inputs)
            assert Transaction.objects.filter(hash__in=inputs).count() == len(inputs)

            # find wallets of sender and recepient
            sender_wallet = Wallet.objects.get(pubkey=t.sender)
            sender_utxos = json.loads(sender_wallet.utxos)

            recepient_wallet = Wallet.objects.get(pubkey=t.recepient)
            recepient_utxos = json.loads(recepient_wallet.utxos)

            # try popping all input transactions from sender wallet
            sender_initial_money = 0
            for txin_hash in inputs:
                found = False
                for utxo in sender_utxos:
                    if utxo['hash'] == txin_hash and utxo['who'] == t.sender:
                        sender_utxos.remove(utxo)
                        sender_initial_money += utxo['amount']
                        found = True
                        break

                # a transaction from inputs is not a UTXO --> invalid
                if not found:
                    return False

            # not enough ccash
            if sender_initial_money < t.amount:
                return False

            # write outputs
            outputs = [
                {
                    'hash': t.hash,
                    'who': t.sender,
                    'amount': sender_initial_money - t.amount
                },
                {
                    'hash': t.hash,
                    'who': t.recepient,
                    'amount': t.amount
                }
            ]

            sender_utxos.append(dict(outputs[0]))
            recepient_utxos.append(dict(outputs[1]))
            sender_wallet.utxos = json.dumps(sender_utxos)
            recepient_utxos.utxos = json.dumps(recepient_utxos)

            sender_wallet.save()
            recepient_wallet.save()

            return t
        except Exception as e:
            print('Transaction.validate_transaction: {e.__class__.__name__}: {e}')
            return None


    @staticmethod
    def create_transaction(recepient, amount):
        try:
            sender = KeyPair.get_public_key()

            recepient_wallet = Wallet.objects.get(pubkey=recepient)
            recepient_utxos = json.loads(recepient_wallet.utxos)

            sender_wallet = Wallet.objects.get(pubkey=sender)
            sender_utxos = json.loads(sender_wallet.utxos)

            inputs = [tx['hash'] for tx in sender_utxos]
            budget = sum(tx['amount'] for tx in sender_utxos)

            if budget < amount:
                return None

            t = Transaction(sender=sender, recepient=recepient, amount=amount, inputs=inputs)
            t.sign()

            # transaction outputs
            outputs = [
                {
                    'hash': t.hash,
                    'who': t.sender,
                    'amount': budget - amount
                },
                {
                    'hash': t.hash,
                    'who': t.recepient,
                    'amount': amount
                }
            ]
            t.outputs = json.dumps(outputs)

            # update wallets
            sender_wallet.utxos = json.dumps([outputs[0]])
            recepient_wallet.utxos = json.dumps(recepient_utxos + [outputs[1]])

            sender_wallet.save()
            recepient_wallet.save()

            return t

        except Exception as e:
            print(f'Transaction.create:{e.__class__.__name__}: {e}')
            return None

