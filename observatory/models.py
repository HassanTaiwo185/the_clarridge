from django.db import models

# Create your models here.
from django.conf import settings
from django.db import models
from django.utils.text import slugify


class ObservatoryPost(models.Model):
    class Category(models.TextChoices):
        RESEARCH = 'research', 'Research'
        ESSAYS = 'essays', 'Essays'
        STUDENT_VOICES = 'student_voices', 'Student Voices'
        INTERVIEWS = 'interviews', 'Interviews'
        PUBLICATIONS = 'publications', 'Publications'

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True, blank=True)

    category = models.CharField(max_length=20, choices=Category.choices)

    summary = models.TextField(blank=True)
    content = models.TextField(blank=True, help_text="Full body content of the post.")

    cover_image = models.ImageField(upload_to='observatory/covers/', null=True, blank=True)

    read_time_minutes = models.PositiveIntegerField(default=5)

    is_featured = models.BooleanField(default=False)

    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='observatory_posts',
    )

    date_posted = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_posted']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while ObservatoryPost.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.category})"
