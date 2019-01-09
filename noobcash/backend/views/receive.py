from django.http import HttpResponse, HttpResponseBadRequest
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from noobcash.backend.transaction import Transaction
from noobcash.backend.block import Block
from noobcash.backend import consensus


@method_decorator(csrf_exempt, name='dispatch')
class ReceiveTransaction(View):
    '''
    View that receives a new transaction from another client.
    Everything is done in `validate_transaction()`
    '''
    def post(self, request):
        trans_json_string = request.POST.get('transaction')
        res = Transaction.validate_transaction(trans_json_string)

        status = 200 if res != 'error' else 400
        return HttpResponse(res, status=status)


@method_decorator(csrf_exempt, name='dispatch')
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
        res = Block.validate_block(block_json_string)

        if res == 'consensus':
            res = consensus.consensus()
            return HttpResponse(res)

        if res == 'ok':
            return HttpResponse(res)

        return HttpResponseBadRequest(res)
