from django.db import models

# Create your models here.
from django.db import models


class TeamMember(models.Model):
    name = models.CharField(max_length=255)
    office = models.CharField(max_length=255, blank=True, help_text="e.g. Research & Publications")
    contact = models.CharField(max_length=255, blank=True, help_text="Phone number or email")
    bio = models.TextField(blank=True)
    photo = models.ImageField(upload_to='team/photos/', null=True, blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name
