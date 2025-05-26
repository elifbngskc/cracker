from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.management.base import BaseCommand
from datetime import timedelta, date

MEAL_CHOICES = [
    ('breakfast', 'Breakfast'),
    ('lunch', 'Lunch'),
    ('dinner', 'Dinner'),
    ('snack', 'Snack'),
]




class Profile(models.Model):
    ACTIVITY_LEVEL_CHOICES = [
            (1.2, "Sedentary (little to no exercise)"),
            (1.375, "Lightly active (1–3 times a week)"),
            (1.55, "Moderately active (3–5 times a week)"),
            (1.725, "Very active (6–7 times a week)"),
            (1.9, "Extra active (intense daily training)"),]

    GENDER_CHOICES = [('male', 'Male'), ('female', 'Female')]
            
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    age = models.IntegerField()
    weight = models.FloatField(help_text="kg")
    height = models.FloatField(help_text="cm")
    gender = models.CharField(max_length=6, choices=GENDER_CHOICES)
    activity_level = models.FloatField(choices=ACTIVITY_LEVEL_CHOICES, default=1.2)
    goal = models.CharField(max_length=10, choices=[('maintain', 'Maintain'), ('lose', 'Lose weight'), ('gain', 'Gain weight')], default='maintain')

    def calculate_bmr(self):
        if self.gender == 'male':
            return (10 * self.weight) + (6.25 * self.height) - (5 * self.age) + 5
        else:
            return (10 * self.weight) + (6.25 * self.height) - (5 * self.age) - 161

    def daily_calories(self):
        return self.calculate_bmr() * self.activity_level

    def daily_macros(self):
        goal = self.goal  # Use the goal stored in the profile

        total = self.daily_calories()

        if goal == "lose":
            total -= 500
        elif goal == "gain":
            total += 500

        return {
            'calories': round(total),
            'protein_g': round((total * 0.3) / 4),
            'carbs_g': round((total * 0.4) / 4),
            'fat_g': round((total * 0.3) / 9),
            }

class FoodItem(models.Model):
    name = models.CharField(max_length=255, unique=True)
    calories = models.FloatField(null=True, blank=True)
    carbohydrates = models.FloatField(null=True, blank=True)
    fats = models.FloatField(null=True, blank=True)
    proteins = models.FloatField(null=True, blank=True)
    fiber = models.FloatField(null=True, blank=True)

    def __str__(self):
        return self.name

class EatenFood(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    food = models.ForeignKey(FoodItem, on_delete=models.CASCADE)
    meal_type = models.CharField(max_length=10, choices=MEAL_CHOICES)
    quantity = models.FloatField(default=1.0, help_text="Quantity in servings")
    date = models.DateField(default=timezone.now)

    def total_nutrients(self):
        return {
            'calories': self.food.calories * self.quantity if self.food.calories else 0,
            'carbohydrates': self.food.carbohydrates * self.quantity if self.food.carbohydrates else 0,
            'fats': self.food.fats * self.quantity if self.food.fats else 0,
            'proteins': self.food.proteins * self.quantity if self.food.proteins else 0,
            'fiber': self.food.fiber * self.quantity if self.food.fiber else 0,
        }
    

class Command(BaseCommand):
    help = 'Deletes EatenFood entries older than 15 days'

    def handle(self, *args, **kwargs):
        cutoff = date.today() - timedelta(days=15)
        deleted, _ = EatenFood.objects.filter(date__lt=cutoff).delete()
        self.stdout.write(f"Deleted {deleted} old EatenFood records.")