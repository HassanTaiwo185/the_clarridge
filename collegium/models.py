from django.db import models


class CollegiumMember(models.Model):
    member_name = models.CharField(max_length=255)
    photo = models.ImageField(upload_to='collegium/photos/')
    school = models.CharField(max_length=255)
    field = models.CharField(max_length=255)

    class Meta:
        ordering = ['member_name']

    def __str__(self):
        return self.member_name