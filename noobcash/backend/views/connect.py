# connect.py

import copy
import json
import requests

from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseServerError, JsonResponse
from django.views import View

from noobcash.backend.transaction import Transaction
from noobcash.backend.block import Block
from noobcash.backend import state, keypair, broadcast, settings, miner

################################################################################

class InitAsClient(View):
    '''CLIENT ONLY'''
    def post(self, request):
        host = request.POST.get('host')

        with state.lock:
            # too safe
            if state.token:
                return HttpResponseBadRequest()

            # hit the coordinator jack
            keypair.generate_keypair()

        api = f'{settings.COORDINATOR}/client_connect/'
        data = {
            'host': host,  # <-- this is our url
            'pubkey': state.pubkey
        }

        response = requests.post(api, data=data)
        if response.status_code != 200:
            return HttpResponseBadRequest()

        return HttpResponse(state.token)


class InitAsServer(View):
    '''SERVER ONLY'''
    def post(self, request):
        count = int(request.POST.get('num_participants'))
        host = request.POST.get('host')

        if count < 2:
            return HttpResponseBadRequest('need >= 2 participants')

        # we are totally safe now
        with state.lock:
            # only once
            if state.pubkey:
                return HttpResponseBadRequest()

            keypair.generate_keypair()

            state.num_participants = count
            state.participant_id = 0
            state.utxos = { }
            state.utxos[state.pubkey] = []

            state.participants[state.pubkey] = {
                'host': host,
                'id': state.participant_id
            }

        return HttpResponse(state.token)


class ClientConnect(View):
    '''SERVER ONLY'''
    def post(self, request):
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

            # all clients connected, send out 'accepted' messages
            if len(state.participants) == state.num_participants:

                # cache list of other hosts
                state.other_hosts = [p['host'] for p in state.participants.values() if p['id'] != state.participant_id]

                # create genesis block
                if not Block.create_genesis_block(state.num_participants):
                    return HttpResponseBadRequest()

                for p in state.participants.values():
                    if p['id'] == state.participant_id:
                        continue

                    requests.post(p['host'] + '/client_accepted/', {
                        'participant_id': p['id'],
                        'participants': json.dumps(state.participants),
                        'genesis_block': state.blockchain[0].dump_sendable(),
                        'genesis_utxos': json.dumps(state.utxos)
                    })

                # after everyone has connected, send transactions
                # print(json.dumps(state.participants, indent=4))
                for pubkey in state.participants:
                    if pubkey == state.pubkey:
                        continue

                    res = Transaction.create_transaction(pubkey, 100)
                    if not res:
                        return HttpResponseServerError()

                    broadcast.broadcast('receive_transaction', {'transaction': res.dump_sendable()}, wait=True)

                miner.start_if_needed()

            return HttpResponse()


class ClientAccepted(View):
    '''CLIENT ONLY'''
    def post(self, request):
        participant_id = int(request.POST.get('participant_id'))
        participants = json.loads(request.POST.get('participants'))
        genesis_block_json = request.POST.get('genesis_block')
        genesis_utxos = json.loads(request.POST.get('genesis_utxos'))

        # print('accepted', request.POST)
        with state.lock:
            if len(state.participants) > 0:
                return HttpResponseBadRequest()

            state.participant_id = participant_id
            state.participants = participants
            state.num_participants = len(state.participants)

            # cache list of other hosts
            state.other_hosts = [p['host'] for p in state.participants.values() if p['id'] != state.participant_id]

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
