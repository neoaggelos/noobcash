# state.py
# Global state variables (excellent design choices)

from threading import RLock

################################################################################

# Lock this before changing the global state
lock = RLock()

# List of validated blocks
blockchain = []

# List of valid transactions not yet in a block
transactions = []

# List of participants `participants[pubkey] = {host, id}`
participants = {}

# Number of participants
num_participants = -1

# numeric id of participant, given by server
# participant_id==0  --> participant is coordinator
participant_id = -1

# Private and public key of this participant
pubkey = None
privkey = None

# Unspent transactions of each participant
# `utxos[pubkey] = [{transaction_id, who, amount}]`
utxos = {}

# pid of miner (if running)
miner_pid = None

# Genesis block and utxos. Makes validating easier
genesis_block = None
genesis_utxos = []
