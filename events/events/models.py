from django.db import models
from django.urls import reverse



class Event(models.Model):
    end_datetime = models.DateTimeField('end_datetime')
    start_datetime = models.DateTimeField('start_datetime')
    description = models.CharField(max_length=200, blank=True)

    def get_absolute_url(self):
        return reverse('event', args=(self.id,))
