# broadcast.py

import requests
from noobcash.backend import state

def broadcast(api: str, message: dict, wait=False):
    '''hit `{host}/{api}/` of all hosts, with data `message`'''

    kwargs = {}
    if not wait:
        kwargs['timeout'] = 0.001

    for h in state.other_hosts:
        try:
            r = requests.post(f'{h}/{api}/', message, **kwargs)

            # cant do too much
            if r.status_code != 200:
                print(f'broadcast: Request "{h}/{api}" failed')

        except requests.exceptions.Timeout:
            print(f'broadcast: Request "{h}/{api}" timed out')
            pass



###############################################################################################

import json
import sys

if __name__ == '__main__':
    api = sys.argv[1]
    message = json.loads(sys.argv[2])
    hosts = json.loads(sys.argv[3])

    broadcast(api, message, hosts)
