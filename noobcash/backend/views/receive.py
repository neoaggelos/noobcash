from django.http import HttpResponse
from django.views import View

from noobcash.backend.transaction import Transaction
from noobcash.backend.block import Block

class ReceiveTransaction(View):
    '''
    View that receives a new transaction from another client.
    Everything is done in `validate_transaction()`
    '''
    def post(request):
        trans_json_string = request.POST['transaction']
        res = Transaction.validate_transaction(trans_json_string)

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
    def post(request):
        block_json_string = request.POST['block']
        res = Block.validate_block(block_json_string)

        if res == 'consensus':
            # TODO: hit up everyone and ask for their blockchains, keep largest

            result = 'ok/error'
            return HttpResponse(result)

        if res == 'ok':
            return HttpResponse(res)

        return HttpResponse(res, status=400)