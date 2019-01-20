import requests
import json

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
        keep_begging = False
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

            keep_begging = not miner.start_if_needed()

        # DISCUSS: also do this when creating blocks?
        # not the brightest idea
        for h in state.other_hosts:
            if not keep_begging:
                break

            # we validated a block and now we have very few transactions
            # hard-working beggars have no shame
            print(f'receive_block/: begging {h} for transactions')
            try:
                response = requests.get(f'{h}/get_pending_transactions/')
                if response.status_code != 200:
                    raise Exception('begging failed')

                new_transactions = json.loads(response.json()['transactions'])

                with state.lock:
                    for tx_json in new_transactions:
                        res, t = Transaction.validate_transaction(tx_json)

                    keep_begging = not miner.start_if_needed()
            except Exception as e:
                print(f'receive_block/: {e.__class__.__name__}: {e}')

        if keep_begging:
            print(f'receive_block/: asked around, no one else has enough transactions')

        return HttpResponse(res)
