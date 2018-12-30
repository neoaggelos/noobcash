from django.db import models

class KeyPair(models.Model):
    pubkey = models.TextField()
    privkey = models.TextField()

    @staticmethod
    def generate_keys():
        if KeyPair.objects.filter(id=1).exists():
            return

        # TODO: grow a pair
        pair = KeyPair(id=1, pubkey='public', privkey='private')
        pair.save()

    @staticmethod
    def get_private_key():
        KeyPair.generate_keys()
        return KeyPair.objects.get(id=1).privkey

    @staticmethod
    def get_public_key():
        KeyPair.generate_keys()
        return KeyPair.objects.get(id=1).pubkey
