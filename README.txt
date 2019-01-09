================================================================================
NOOBCASH
================================================================================

A simple blockchain system for validating transactions using Proof of work.


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


================================================================================
INSTALLATION
================================================================================

Install required packages:
$ sudo apt-get install python3 python3-pip python3-requests python3-virtualenv

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

Usage (start server):
$ cd noobcash
$ source .venv/bin/activate
$ python manage.py runserver [port]

And then in a separate terminal:
$ cd noobcash
$ source .venv/bin/activate
$ python client.py [host] [port] -n NUM_PARTICIPANTS (for the coordinator)
$ python client.py [host] [port] (for participants)
