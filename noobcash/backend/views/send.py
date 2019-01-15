import json

from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.views import View

from noobcash.backend.transaction import Transaction
from noobcash.backend.block import Block
from noobcash.backend import multicast, state, miner


class CreateAndSendTransaction(View):
    '''
    Create a transaction and multicast to all participants.
    '''
    def post(self, request):
        recepient = request.POST.get('recepient')
        amount = request.POST.get('amount')
        token = request.POST.get('token')

        with state.lock:
            if state.token != token:
                return HttpResponseBadRequest('invalid token')

            res = Transaction.create_transaction(recepient, amount)
            if res is None:
                return HttpResponseBadRequest('invalid transaction')

        multicast.multicast('receive_transaction', {'transaction': res.dump_sendable()}, [p['host'] for p in state.participants.values() if p['id'] != state.participant_id])

        miner.start_if_needed()

        return HttpResponse()


class CreateAndSendBlock(View):
    '''
    The miner uses this view to notify server that a correct nonce was found
    The participant creates the block, appends to their own blockchain and multicasts

    `create_block` will also make sure that the nonce is indeed correct
    '''
    def post(self, request):
        transactions = json.loads(request.POST.get('transactions'))
        nonce = int(request.POST.get('nonce'))
        sha = request.POST.get('sha')
        token = request.POST.get('token')

        if token != state.token:
            return HttpResponseBadRequest('invalid token')

        miner.stop()

        # FIXME: start miner after sending?
        with state.lock:
            res = Block.create_block(transactions, nonce, sha)
            miner.start_if_needed()

            if res is None:
                return HttpResponseBadRequest()

        multicast.multicast('receive_block', {'block': res.dump_sendable()}, [p['host'] for p in state.participants.values() if p['id'] != state.participant_id])

        return HttpResponse()


class GetBlockchain(View):
    '''
    Return current blockchain
    '''
    def get(self, request):
        with state.blockchain_public_lock:
            # DISCUSS: we do not include the genesis block
            return JsonResponse({
                'blockchain': json.dumps(state.blockchain_public)
            })


class GetBalance(View):
    '''
    Return current wallet amount for each participant,
    as a dict {
        id: {
            'pubkey': string,
            'amount': nbc
        }
    }

    It merely sums the amount of validated utxos for each user
    '''
    def get(self, request):
        with state.lock:
            result = {}
            for pubkey in state.participants:
                result[state.participants[pubkey]['id']] = {
                    'host': state.participants[pubkey]['host'],
                    'pubkey': pubkey,
                    'amount': sum(x['amount'] for x in state.valid_utxos[pubkey]),
                    'this': state.participant_id == state.participants[pubkey]['id']
                }

        return JsonResponse(result)


class GetLatestBalance(View):
    '''
    Return current wallet amount for each participant,
    as a dict {
        id: {
            'pubkey': string,
            'amount': nbc
        }
    }

    It merely sums the amount of validated utxos for each user
    '''
    def get(self, request):
        with state.lock:
            result = {}
            for pubkey in state.participants:
                result[state.participants[pubkey]['id']] = {
                    'host': state.participants[pubkey]['host'],
                    'pubkey': pubkey,
                    'amount': sum(x['amount'] for x in state.utxos[pubkey]),
                    'this': state.participant_id == state.participants[pubkey]['id']
                }

        return JsonResponse(result)


class GetTransactions(View):
    '''
    Return list of transactions from last block
    '''
    def get(self, request):
        with state.lock:
            result = []
            for tx_json_string in state.blockchain[-1].transactions:
                tx = Transaction(**json.loads(tx_json_string))

                result.append({
                    'sender_id': state.participants[tx.sender]['id'],
                    'recepient_id': state.participants[tx.recepient]['id'],
                    'id': tx.id,
                    'amount': tx.amount
                })

        return JsonResponse({'transactions': result})


class GetAllTransactions(View):
    '''
    Return list of transactions from all blocks
    '''
    def get(self, request):
        with state.lock:
            blocks = []
            for block in state.blockchain:
                txs = []
                for tx_json_string in block.transactions:
                    tx = Transaction(**json.loads(tx_json_string))

                    txs.append({
                        'sender_id': state.participants[tx.sender]['id'],
                        'recepient_id': state.participants[tx.recepient]['id'],
                        'id': tx.id,
                        'amount': tx.amount
                    })

                blocks.append({
                    'index': block.index,
                    'transactions': txs,
                    'hash': block.current_hash,
                    'prev': block.previous_hash
                })

            # txs = []
            # for tx in state.transactions:
            #     txs.append({
            #         'sender_id': state.participants[tx.sender]['id'],
            #         'sender': tx.sender,
            #         'recepient_id': state.participants[tx.recepient]['id'],
            #         'recepient': tx.recepient,
            #         'amount': tx.amount
            #     })

            # if txs:
            #     blocks.append({
            #         'index': 'pending',
            #         'transactions': txs
            #     })

        return JsonResponse({'blocks': blocks})