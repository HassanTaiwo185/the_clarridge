from django.conf import settings
from django.db import models
from django.utils.text import slugify


class Article(models.Model):
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='articles',  # user.articles.all() -> everything they uploaded
    )

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True, blank=True)

    author_name = models.CharField(
        max_length=255,
        help_text="The actual writer of the article — may differ from the person uploading it.",
    )

    summary = models.TextField(
        help_text="Short description/abstract of the article."
    )

    pdf_file = models.FileField(
        upload_to='articles/pdfs/',
    )

    date_written = models.DateField(
        help_text="The date the article was originally written by the author."
    )

    date_posted = models.DateTimeField(
        auto_now_add=True,
        help_text="Automatically set when the article is uploaded to the platform.",
    )

    class Meta:
        ordering = ['-date_posted']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while Article.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} by {self.author_name}"