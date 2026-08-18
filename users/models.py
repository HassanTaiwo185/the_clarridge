from django.contrib.auth.models import User
from django.db import models


class Profile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )

    passport_photo = models.ImageField(
        upload_to='passport_photos/'
    )

    phone_number = models.CharField(
        max_length=20
    )

    date_of_birth = models.DateField()

    def __str__(self):
        return self.user.username