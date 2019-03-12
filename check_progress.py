# Helper script, just to keep track of progress

import requests

total = 0
max_size = -1
for x in range(1, 6):
        r = requests.get(f'http://192.168.0.{x}:8000/get_num_pending_transactions/')
        num_pending = r.json()['num_pending']

        r = requests.get(f'http://192.168.0.{x}:8000/get_num_blocks_created/')
        num_blocks = r.json()['num_blocks']
        total += num_blocks

        r = requests.get(f'http://192.168.0.{x}:8000/get_blockchain_length/')
        size = r.json()['blockchain_length']
        max_size = max(size, max_size)

        print('id', x, '\tblocks created:', num_blocks, '\tpending transactions:', num_pending, '\tblockchain size:', size)

print('blockchain: ', max_size, '\ttotal blocks:', total)
