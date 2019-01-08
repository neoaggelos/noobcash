# connect.py

import copy
import requests

from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseServerError
from django.views import View

from noobcash.backend.transaction import Transaction
from noobcash.backend.block import Block
from noobcash.backend import state, keypair, multicast, settings

################################################################################

class InitAsClient(View):
    '''CLIENT ONLY'''
    def post(request):
        host = request.POST.get('host')

        with state.lock:
            # too safe
            if state.token:
                return HttpResponseBadRequest()

            # hit the coordinator jack
            keypair.generate_keys()
            api = f'{settings.COORDINATOR_HOST}/client_connect/'
            data = {
                'host': host,  # <-- this is our url
                'pubkey': state.pubkey
            }

            response = requests.post(api, data)
            if response.status_code != 200:
                return HttpResponseBadRequest()

        return HttpResponse(state.token)


class InitAsServer(View):
    '''SERVER ONLY'''
    def post(request):
        count = request.POST.get('num_participants')
        host = request.POST.get('host')

        # we are totally safe now
        with state.lock:
            # only once
            if state.pubkey:
                return HttpResponseBadRequest()

            state.num_participants = count
            state.participant_id = 0
            state.utxos = { }
            state.utxos[state.pubkey] = []

            keypair.generate_keypair()
            state.participants[state.pubkey] = {
                'host': host,
                'id': state.participant_id
            }

            if not Transaction.create_genesis_transaction(count):
                return HttpResponseServerError()

        return HttpResponse(state.token)


class ClientConnect(View):
    '''SERVER ONLY'''
    def post(request):
        host = request.POST.get('host')
        pubkey = request.POST.get('pubkey')

        # safe as a kite
        with state.lock:
            if state.num_participants == -1 or state.participant_id != 0 or pubkey in state.participants:
                return HttpResponseBadRequest()

            next_id = len(state.participants)
            state.participants[pubkey] = {
                'host': host,
                'id': next_id
            }
            state.utxos[pubkey] = []

            if not Transaction.create_transaction(pubkey, 100, start_miner=False):
                return HttpResponseServerError()

            # all clients connected, send out 'accepted' messages
            if len(state.participants) == state.num_participants:
                # create genesis block
                Block.create_genesis_block()

                for p in state.participants:
                    if p['id'] == state.participant_id:
                        continue

                    requests.post(p['host'] + '/client_accepted/', json={
                        'participant_id': p['id']
                        'participants': state.participants,
                        'genesis_block': state.blockchain[0].dump_sendable(),
                        'genesis_utxos': state.utxos
                    })

            return HttpResponse()


class ClientAccepted(View):
    '''CLIENT ONLY'''
    def post(request):
        participant_id = request.POST.get('participant_id')
        participants = request.POST.get('participants')
        genesis_block_json = request.POST.get('genesis_block')
        genesis_utxos = request.POST.get('genesis_utxos')

        with state.lock:
            if len(state.participants) > 0:
                return HttpResponseBadRequest()

            state.participant_id = participant_id
            state.participants = json.loads(participants)
            state.num_participants = len(state.participants)

            # initial blockchain contains genesis block
            # DISCUSS: we just `logged in`, do we trust him or should we check
            state.utxos = copy.deepcopy(genesis_utxos)
            state.blockchain = [Block(**json.loads(genesis_block_json), index=0)]
            state.valid_utxos = copy.deepcopy(state.utxos)

            # keep a backup of the genesis block and its utxos.
            # DISCUSS: this is to make validation easier when asking for consensus
            state.genesis_utxos = copy.deepcopy(genesis_utxos)
            state.genesis_block = Block(**json.loads(genesis_block_json), index=0)

        return HttpResponse()


class GetParticipantsList(View):
    '''Return list of known participants'''
    def get(request):
        return JsonResponse(state.participants)
