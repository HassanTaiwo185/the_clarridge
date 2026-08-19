from django.db import models


class CalendarEvent(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    week_label = models.CharField(
        max_length=50,
        help_text="Display text for the week range, e.g. 'Week 1' or 'Weeks 1-2'.",
    )

    start_date = models.DateField()
    end_date = models.DateField()

    class Meta:
        ordering = ['start_date']

    def save(self, *args, **kwargs):
        # keep validation simple and consistent — end can't be before start
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.week_label})"