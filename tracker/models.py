from django.db import models

# Create your models here.
from django.db import models

class FoodItem(models.Model):
    name = models.CharField(max_length=255, unique=True)
    calories = models.FloatField(null=True, blank=True)
    carbohydrates = models.FloatField(null=True, blank=True)
    fats = models.FloatField(null=True, blank=True)
    proteins = models.FloatField(null=True, blank=True)
    fiber = models.FloatField(null=True, blank=True)

    def __str__(self):
        return self.name
