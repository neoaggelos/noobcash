from django.http import HttpResponse, HttpResponseBadRequest
from django.views import View

from noobcash.backend.transaction import Transaction
from noobcash.backend.block import Block
from noobcash.backend import multicast, state

class CreateAndSendTransaction(View):
    '''
    Create a transaction and multicast to all participants
    '''
    def post(request):
        recepient = request.POST['recepient']
        amount = request.POST['amount']
        res = Transaction.create_transaction(recepient, amount)

        if res is None:
            return HttpResponseBadRequest()

        multicast.multicast('receive_transaction', {'transaction': res.dump_sendable()}, [p['host'] for p in state.participants])

        status = 200 if res != 'error' else 400
        return HttpResponse(res, status=status)


class CreateAndSendBlock(View):
    '''
    The miner uses this view to notify server that a correct nonce was found
    The server creates the block, appends to his own blockchain and multicasts

    `create_block` will also make sure that nonce is indeed correct
    '''
    def post(request):
        transactions = request.POST['transactions']
        nonce = request.POST['nonce']
        res = Block.create_block(transactions, nonce)

        if res is None:
            return HttpResponseBadRequest()

        multicast.multicast('receive_block', {'block': res.dump_sendable()}, [p['host'] for p in state.participants])

        return HttpResponse(res, status=400)
