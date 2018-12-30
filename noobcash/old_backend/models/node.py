from django.db import models

class NodeInfo(models.Model):
    num_participants = models.IntegerField(null=True)
    is_coordinator = models.BooleanField(null=False)
    miner_pid = models.IntegerField(null=True, default=None)

class Node(models.Model):
    server = models.TextField(null=False)
    pubkey = models.TextField(null=False)

