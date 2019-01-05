# connect.py

import requests

from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseServerError
from django.views import View

from noobcash.backend.transaction import Transaction
from noobcash.backend import state, keypair, multicast
from noobcash import settings

class InitAsServerView(View):
    '''SERVER ONLY'''
    def post(request):
        count = request.POST.get('num_participants')

        # eh well
        host = request.get_host().replace({'localhost': '127.0.0.1'})

        # assert we are indeed meant to be the coordinator
        if request.get_host() != settings.COORDINATOR:
            return HttpResponseBadRequest("no im not him")

        # we are totally safe now
        with state.participants_lock:
            if state.num_participants != -1 or state.participant_id != -1:
                return HttpResponseBadRequest()

            state.num_participants = count
            state.participant_id = 0
            state.utxos[state.pubkey] = []

            keypair.generate_keypair()
            state.participants[state.pubkey] = {
                'host': 'http://' + settings.COORDINATOR,
                'id': state.participant_id
            }

            if not Transaction.create_genesis_transaction(count):
                return HttpResponseServerError()

        return HttpResponse()


class ClientConnectView(View):
    '''SERVER ONLY'''
    def post(request):
        host = request.POST.get('host')
        pubkey = request.POST.get('pubkey')

        # safe as a kite
        with state.participants_lock, state.utxos_lock:
            if state.num_participants == -1 or state.participant_id != 0:
                return HttpResponseBadRequest()

            if pubkey in state.participants:
                return HttpResponseBadRequest()

            next_id = len(state.participants)
            state.participants[pubkey] = {
                'host': host,
                'id': next_id
            }
            state.utxos[pubkey] = []

            if not Transaction.create_transaction(pubkey, 100):
                return HttpResponseServerError()

            # all clients connected, send out 'accepted' messages
            if len(state.participants) == state.num_participants:
                # create genesis block
                Block.create_genesis_block()

                # send information to all participants
                api = 'client_accepted'
                data = {
                    'num_participants': state.num_participants,
                    'participants': state.participants,
                    'blockchain': state.blockchain,
                    'utxos': state.utxos
                }
                hosts = [p['host'] for p in state.participants]

                multicast.multicast(api, data, hosts)

            return HttpResponse()


class InitAsClientView(View):
    '''CLIENT ONLY'''
    def post(request):
        with state.participants_lock:
            # too safe
            if state.num_participants != -1:
                return HttpResponseBadRequest()

            # hit the coordinator jack
            keypair.generate_keys()
            api = f'http://{settings.COORDINATOR}/client_connect'
            data = {
                'host': 'http://' + request.get_host(),  # <-- this is our url
                'pubkey': state.pubkey
            }

            response = requests.post(api, data)
            if response.status_code != 200:
                return HttpResponseBadRequest()

        return HttpResponse()


class ClientAcceptedView(View):
    '''CLIENT ONLY'''
    def post(request):
        num_participants = request.POST.get('num_participants')
        participants = request.POST.get('participants')
        blockchain = request.POST.get('blockchain')
        utxos = request.POST.get('utxos')

        with state.participants_lock:
            if len(state.participants) > 0:
                return HttpResponseBadRequest()

            state.num_participants = num_participants
            state.participants = json.loads(participants)

            for p in state.participants:
                if request.get_host() in p['host']:
                    state.participant_id = p['id']

            # initial blockchain contains genesis block
            # DISCUSS: we just `logged in`, do we trust him or should we check
            with state.blockchain_lock, state.utxos_lock:
                state.utxos = utxos
                state.blockchain = blockchain

        return HttpResponse()


class GetParticipantsListView(View):
    '''Return list of known participants'''
    def get(request):
        return JsonResponse(state.participants)
