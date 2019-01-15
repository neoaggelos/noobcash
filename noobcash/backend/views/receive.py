from django.http import HttpResponse, HttpResponseBadRequest
from django.views import View

from noobcash.backend.transaction import Transaction
from noobcash.backend.block import Block
from noobcash.backend import consensus, settings, state, miner


class ReceiveTransaction(View):
    '''
    View that receives a new transaction from another client.
    Everything is done in `validate_transaction()`
    '''
    def post(self, request):
        trans_json_string = request.POST.get('transaction')
        with state.lock:
            res, t = Transaction.validate_transaction(trans_json_string)
            miner.start_if_needed()

        status = 200 if res != 'error' else 400
        return HttpResponse(res, status=status)


class ReceiveBlock(View):
    '''
    View that receives a new block from another client.
    Everything is done in `validate_block()`.

    In case consensus is required, all participants are asked and
    the largest valid chain is adopted. This is done in `chain_consensus()`
    In general, consensus is gonna be pretty slow.
    '''
    def post(self, request):
        block_json_string = request.POST.get('block')

        miner.stop()
        with state.lock:
            res = Block.validate_block(block_json_string)

            if res == 'error':
                return HttpResponseBadRequest(res)

            if res == 'consensus':
                print('need consensus vote')
                res = consensus.consensus()

            if res == 'ok':
                print('block is ok')

            if res == 'dropped':
                print('dropping')

            miner.start_if_needed()
            return HttpResponse(res)
