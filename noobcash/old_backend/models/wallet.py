# wallet.py

from django.db import models

class Wallet(models.Model):
    pubkey = models.TextField()
    utxos = models.TextField() # JSON string of [tid_1, tid_2, ...]
