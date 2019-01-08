# multicast.py

import requests

def multicast(api: str, message: dict, hosts: list):
    '''hit `{host}/{api}/` of all hosts, with data `message`'''

    for h in hosts:
        r = requests.post(f'{h}/{api}/', message)

        # cant do too much
        if r.status_code != 200:
            print(f'multicast: Request "{host}/{api}", json={message} failed')


###############################################################################################

import json
import sys

if __name__ == '__main__':
    api = sys.argv[1]
    message = json.loads(sys.argv[2])
    hosts = json.loads(sys.argv[3])

    multicast(api, message, hosts)
