from django.conf import settings
from django.db import models


class Address(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="addresses"
    )
    country = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    street = models.CharField(max_length=255)
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=50)
    building = models.CharField(max_length=100, blank=True, null=True)
    apartment = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        is_first_address = (
            self._state.adding and not Address.objects.filter(user=self.user).exists()
        )
        # A user must always have exactly one default address once they have
        # any address at all - so the very first one is forced to be it,
        # regardless of what the client sent.
        if is_first_address:
            self.is_default = True

        make_default = self.is_default
        super().save(*args, **kwargs)

        if make_default:
            Address.objects.filter(
                user=self.user, is_default=True
            ).exclude(pk=self.pk).update(is_default=False)

    def __str__(self):
        return f"{self.user.email} - {self.city}, {self.street}"
