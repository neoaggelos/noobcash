# state.py
# Global state variables (excellent design choices)

from threading import RLock

################################################################################

# List of validated blocks
blockchain = []
blockchain_lock = RLock()

# List of valid transactions not yet in a block
transactions = []
transactions_lock = RLock()

# List of participants `participants[pubkey] = {host, id}`
participants = {}
participants_lock = RLock()

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
utxos_lock = RLock()

# pid of miner (if running)
miner_pid = None