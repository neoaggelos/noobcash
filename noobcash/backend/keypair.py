from noobcash.backend import state

from Crypto.PublicKey import RSA
from Crypto.Hash import SHA384

# Generate keypair and store in global state
def generate_keypair():
    if (state.privkey and state.pubkey) is not None:
        return

    rsa_keypair = RSA.generate(2048)

    with state.lock:
        state.privkey = rsa_keypair.exportKey().decode()
        state.pubkey = rsa_keypair.publickey().exportKey().decode()

        # Token is the sha of a part of the private key.
        state.token = SHA384.new(state.privkey[::2]).digest().decode()
