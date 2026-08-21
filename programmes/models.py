from django.db import models
from django.utils.text import slugify


class Programme(models.Model):
    class Status(models.TextChoices):
        UPCOMING = 'upcoming', 'Upcoming'
        OPEN = 'open', 'Open'
        COMPLETED = 'completed', 'Completed'

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True, blank=True)

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.UPCOMING,
    )

    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    cover_image = models.ImageField(upload_to='programmes/covers/', null=True, blank=True)

    description = models.TextField(blank=True)

    class Meta:
        ordering = ['-start_date']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Programme.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.status})"