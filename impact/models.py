from django.db import models

# Create your models here.
from django.db import models


class ImpactStats(models.Model):
    students_reached = models.PositiveIntegerField(default=0)
    universities = models.PositiveIntegerField(default=0)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Impact Stats"
        verbose_name_plural = "Impact Stats"

    def save(self, *args, **kwargs):
        self.pk = 1  # enforce singleton — always overwrite the same row
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass  # prevent deletion entirely

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "Impact Stats"