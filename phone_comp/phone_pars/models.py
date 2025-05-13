from django.db import models


class PhoneData(models.Model):
    model = models.CharField(max_length=120)
    data = models.JSONField(null = True, blank = True)
    class Meta:
        verbose_name = 'Phone Data'
        verbose_name_plural = 'Phone Data'
# Create your models here.
