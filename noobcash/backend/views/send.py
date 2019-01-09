import json

from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.views import View

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from noobcash.backend.transaction import Transaction
from noobcash.backend.block import Block
from noobcash.backend import multicast, state


@method_decorator(csrf_exempt, name='dispatch')
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
                return HttpResponseBadRequest()

            multicast.multicast('receive_transaction', {'transaction': res.dump_sendable()}, [p['host'] for p in state.participants.values() if p['id'] != state.participant_id])

        return HttpResponse()

@method_decorator(csrf_exempt, name='dispatch')
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

        # FIXME: start miner after sending?
        with state.lock:
            res = Block.create_block(transactions, nonce, sha, start_miner=True)
            if res is None:
                return HttpResponseBadRequest()

            multicast.multicast('receive_block', {'block': res.dump_sendable()}, [p['host'] for p in state.participants.values() if p['id'] != state.participant_id])

        return HttpResponse()


@method_decorator(csrf_exempt, name='dispatch')
class GetBlockchain(View):
    '''
    Return current blockchain
    '''
    def get(self, request):
        with state.lock:
            # DISCUSS: we do not include the genesis block
            return JsonResponse({
                'blockchain': [b.dump_sendable() for b in state.blockchain][1:]
            })


@method_decorator(csrf_exempt, name='dispatch')
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
                    'pubkey': pubkey,
                    'amount': sum(x['amount'] for x in state.utxos[pubkey])
                }

        return JsonResponse(result)
