from django.db import models
from django.utils.text import slugify


class Opportunity(models.Model):
    class Category(models.TextChoices):
        SCHOLARSHIP = 'scholarship', 'Scholarship'
        INTERNSHIP = 'internship', 'Internship'
        FELLOWSHIP = 'fellowship', 'Fellowship'
        COMPETITION = 'competition', 'Competition'

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True, blank=True)

    category = models.CharField(
        max_length=20,
        choices=Category.choices,
    )

    deadline = models.DateField()

    description = models.TextField(blank=True)

    details_url = models.URLField(
        blank=True,
        help_text="External link for 'View Details', if applicable.",
    )

    class Meta:
        ordering = ['deadline']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while Opportunity.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.category})"