================================================================================
NOOBCASH
================================================================================

A simple blockchain system for validating transactions using Proof of work.
Created for the `Distributed Systems` course of NTUA ECE.

~ Aggelos Kolaitis

================================================================================
INSTALLATION
================================================================================

Install required packages:
    $ sudo apt-get install python3 python3-pip python3-requests \
                            python3-virtualenv

Setup:
    $ tar xvfz noobcash.tar.gz
    $ cd noobcash
    $ virtualenv .venv
    $ source .venv/bin/activate
    $ pip install .

Edit `noobcash/backend/settings.py` to configure settings:
    * BLOCK_CAPACITY    <-- number of transactions of each block
    * DIFFICULTY        <-- mining difficulty
    * COORDINATOR_HOST  <-- well-known address of coordinator

Usage (start a server for each participant):
    $ cd noobcash
    $ source .venv/bin/activate
    $ python manage.py runserver [port]

And then in a separate terminal:
    $ cd noobcash
    $ source .venv/bin/activate
    $ python client.py [host] [port] -n NUM_PARTICIPANTS (for the coordinator)
    $ python client.py [host] [port] (for participants)


================================================================================
COMMANDS
================================================================================

Commands are given via the client.

help_message = '''
Usage:

$ client.py HOST PORT           Start as participant
$ client.py HOST PORT -n N      Start as coordinator, for N participants

Available commands:

* `t [recepient_id] [amount]`   Send `amount` NBC to `recepient`
* `source [fname]`              Read and send transactions from `fname`
* `view`                        View transactions of the latest block
* `balance`                     View balance of each wallet (as of last validated block)
* `help`                        Print this help message
* `exit`                        Exit client (will not stop server)


Extra commands:

* `view_all`                    View transactions of all validated blocks so far
* `latest_balance`              View balance of each wallet (as of last received transaction)
'''


================================================================================
ARCHITECTURE
================================================================================

Noobcash consists of two main parts, a server (written in Django) and a client
that sends commands to the server via REST API calls.

One participant (well-known to all others) is the coordinator, and the others
are clients. On startup, all clients connect to the coordinator.

After everyone has connected, the coordinator creates the genesis block, which
gives him 100*NUM_PARTICIPANTS coins. Then, he creates a transaction that gives
100 coins to each participant.

Upon receiving BLOCK_CAPACITY valid transactions, the participant starts mining
a new block, by calculating a nonce such that the first DIFFICULTY digits of the
block SHA are zeros. The miner is a separate process, so that the participant
can still handle other incoming requests or blocks. When a correct nonce value
is found, the miner notifies the participant, who creates the new block and
sends it to all other participants as well.

Upon receiving a valid block, the participant compares its `previous_hash` with
the hash of the latest block in the chain. If they match, then the block is
accepted. Otherwise, it is assumed that a different chain has been created, so
the participant asks all the other participants for their blockchains, adopting
the largest one.


================================================================================
IMPLEMENTATION DETAILS
================================================================================

A Transaction object consists of:
    * sender        Public key of sender
    * recepient     Public key of recepient
    * amount        Coins transferred
    * inputs        ids of previous transactions whose UTXOS are spent
    * id            Hash of the above information
    * outputs       Output UTXOS of this transaction
    * signature     Hash encrypted using sender's private key

A Block object consists of:
    * transactions  List of BLOCK_CAPACITY transactions
    * nonce         Integer value so that block hash starts with DIFFICULTY 0s
    * current_hash  Hash of the above
    * previous_hash Hash of the previous block in the chain
    * index         Index of the block in the blockchain
    * timestamp     Time of creation

Each participant keeps track of:
    * blockchain            The currently validated list of blocks
    * public_blockchain     The blockchain (without the genesis block), cached in
                            sendable format. Used for consensus.
    * transactions          List of transactions not yet in a block.
    * utxos                 List of UTXOS as of the latest transaction received.
    * miner_pid             PID of the miner process (if running)

    * participants          A list of all participants (pubkeys, hosts, ids)
    * participant_id        Id of this participant.

    * pubkey/privkey        Public and private key of this participant.
    * token                 Generated by the private key, shared ONLY with the
                            client associated with this participant. Used to
                            verify requests involving creating a new block or
                            a new transaction

    * valid_utxos           List of UTXOS as of the latest valid block. Makes
                            validating incoming blocks easier and faster.
    * genesis_block         Copy of the genesis block.
    * genesis_utxos         Copy of the UTXOS of the genesis block.


================================================================================
SOURCE CODE
================================================================================

./
    manage.py           Used to run the django server
    client.py           Client, sends requests to server

./noobcash/
    urls.py             Endpoints for server
    settings.py         Django settings, not too important

./noobcash/backend/
    state.py            Global state of participant
    settings.py         Noobcash settings, e.g. block capacity
    block.py            Defines `Block` class
    transaction.py      Defines `Transaction` class
    keypair.py          Generates public and private RSA keys
    consensus.py        The algorithm run to achieve consensus
    broadcast.py        Send a message to every participant
    miner.py            Implementation of the miner

./noobcash/backend/views
    connect.py          Views for establishing initial connection
    send.py             Send blocks/transactions, share information
    receive.py          Receive blocks/transactions

================================================================================
OTHER NOTES / IDEAS
================================================================================

See DISCUSSION.txt

Report: https://docs.google.com/document/d/1IrHIxjRZUOIjvZaYtMnH9kDP3d-qEf-OOezrXS8d06o/edit?usp=sharing
Test results: https://docs.google.com/spreadsheets/d/1GeJlyRkASXRo4OadStglT1zQkhTMGkKsU1Fi1CI4aeo/edit?usp=sharing
