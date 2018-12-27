# transaction.py

'''
Implement basic transaction functions
transaction == {
    sender: pubkey of sender
    receiver: pubkey of receiver
    amount: payment amount
    inputs: list of inputs == ['id1', 'id2', ...] <--- ids of transactions where transactions['id'].receiver == this.sender
    outputs: list of outputs == [{'receiver': receiver, 'amount': this.amount}, {'receiver': sender, 'amount': total_from_inputs - this.amount}]
    id: hash of the above info
    signature: 'id' encrypted with sender private key
}
'''

from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA384
import json


########################################################################
SENDER=0
RECEIVER=1
########################################################################

# shortcuts
def dump_transaction(transaction):
    t = dict(transaction)
    for key in ['signature', 'id', 'outputs']:
        try:
            del t[key]
        except:
            pass

    return json.dumps(t, sort_keys=True)


def get_transaction_hash(transaction):
    return SHA384.new(dump_transaction(transaction))

#############################################################################

# check if a dict follows the proper transaction format
def is_transaction(t):
    try:
        for key in ['sender', 'receiver', 'amount', 'inputs', 'id', 'signature']:
            t[key]
        float(t['amount'])

        assert(t['sender'] != t['receiver'])
        assert(isinstance(t['id'], bytes))
        assert(isinstance(t['signature'], bytes))

        assert(isinstance(t['inputs'], list))
        assert(len(set(t['inputs']) == len(t['inputs'])))
        for txi in t['inputs']:
            assert(isinstance(txi, bytes))

        return True
    except (KeyError, ValueError, AssertionError):
        return False


# calculate transaction hash and sign
# with private key (must be the private key of sender)
# NOTE: hash is calculated without `id`, `outputs` and `signature`
#
# @return signed transaction
def sign_transaction(transaction, private_key):
    h = get_transaction_hash(transaction)

    transaction['id'] = h.digest()
    rsa_key = RSA.importKey(private_key)
    signer = PKCS1_v1_5.new(rsa_key)

    transaction['signature'] = signer.sign(h)

    return transaction


# check if signature of transaction is ok
# calculate hash of transaction-hash
# NOTE: hash is calculated without `id`, `outputs` and `signature`
def verify_signature(transaction):
    rsa_key = RSA.importKey(transaction['sender'])
    verifier = PKCS1_v1_5.new(rsa_key)

    hashed = get_transaction_hash(transaction)
    return verifier.verify(hashed, transaction['signature'])


# verify signature of transaction
# validate transaction inputs from wallets
# create outputs and update wallets
#
# @return success, new_wallets, updated_transaction
def validate_transaction(wallets, transaction):
    if not is_transaction(transaction):
        return False, wallets, transaction

    if not verify_signature(transaction):
        return False, wallets, transaction

    # work on a copy, if an error occurs we just discard it
    new_wallet = list(wallets[transaction['sender']])

    # try popping all input transactions from the wallet
    sender_initial_money = 0
    for txin_id in transaction['inputs']:
        found = False
        for utxo in new_wallet:
            if utxo['id'] == txin_id:
                new_wallet.remove(utxo)
                sender_initial_money += utxo['amount']
                found = True
                break

        # a transaction from the inputs is not a UTXO ==> transaction is invalid
        if not found:
            return False, wallets, transaction

    # input transactions are not bringing in enough cash
    if sender_initial_money < transaction['amount']:
        return False, wallets, transaction

    # write transaction outputs
    # this is needed to update wallets when receiving blocks
    transaction['outputs'] = [{
        # outputs[0]: SENDER
        'id': transaction['id'],
        'receiver': transaction['sender'],
        'amount': (sender_initial_money - transaction['amount'])
    }, {
        # outputs[1]: RECEIVER
        'id': transaction['id'],
        'receiver': transaction['receiver'],
        'amount': transaction['amount']
    }]

    # append them to the wallets as well
    wallets[transaction['sender']] = new_wallet
    wallets[transaction['sender']].append(dict(transaction['outputs'][SENDER]))
    wallets[transaction['receiver']].append(dict(transaction['outputs'][RECEIVER]))

    return True, wallets, transaction


# TODO
# @return success, transaction, new_wallets
def create_transaction(wallets, sender, receiver, amount):
    transaction = {}

    if sender not in wallets or receiver not in wallets:
        return False, None, wallets

    transaction['sender'] = sender
    transaction['receiver'] = receiver
    transaction['amount'] = amount

    # NOTE: we send all UTXOs as transaction inputs
    # this is not required, but it makes me sleep better at night
    transaction['inputs'] = [tx['id'] for tx in wallets[transaction['sender']]]
    sender_initial_money = sum([tx['amount'] for tx in wallets[transaction['sender']]])

    # pyramid schemers begone
    if sender_initial_money < amount:
        return False, None, wallets

    # sign transaction
    transaction = sign_transaction(transaction, "MY_PRIVATE_KEY")
    transaction['outputs'] = [{
        'id': transaction['id'],
        'receiver': transaction['sender'],
        'amount': (sender_initial_money - amount)
    }, {
        'id': transaction['id'],
        'receiver': transaction['receiver'],
        'amount': amount
    }]

    # update wallets
    wallets[transaction['sender']] = [dict(transaction['outputs'][SENDER])]
    wallets[transaction['receiver']].append(dict(transaction['outputs'][RECEIVER]))

    return True, transaction, wallets
