from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models


def validate_file_size(value):
    max_size_mb = 5
    if value.size > max_size_mb * 1024 * 1024:
        raise ValidationError(f"File size must not exceed {max_size_mb}MB.")


class Application(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SHORTLISTED = 'shortlisted', 'Shortlisted'
        APPROVED = 'approved', 'Approved'

    # Personal Information
    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone_number = models.CharField(max_length=20)
    date_of_birth = models.DateField()

    passport_photo = models.ImageField(
        upload_to='applications/passport_photos/',
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png']),
            validate_file_size,
        ],
    )

    cv_transcript = models.FileField(
        upload_to='applications/cv_transcripts/',
        validators=[
            FileExtensionValidator(allowed_extensions=['pdf']),
            validate_file_size,
        ],
    )

    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.PENDING,
    )

    date_applied = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_applied']

    def __str__(self):
        return f"{self.full_name} ({self.status})"