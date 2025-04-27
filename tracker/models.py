from django.db import models
from django.contrib.auth.models import User

ACTIVITY_LEVEL_CHOICES = [
    (1.2, "Sedentary (little to no exercise)"),
    (1.375, "Lightly active (1–3 times a week)"),
    (1.55, "Moderately active (3–5 times a week)"),
    (1.725, "Very active (6–7 times a week)"),
    (1.9, "Extra active (intense daily training)"),]

GENDER_CHOICES = [('male', 'Male'), ('female', 'Female')]

class Profile(models.Model):
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    age = models.IntegerField()
    weight = models.FloatField(help_text="kg")
    height = models.FloatField(help_text="cm")
    gender = models.CharField(max_length=6, choices=GENDER_CHOICES)
    activity_level = models.FloatField(choices=ACTIVITY_LEVEL_CHOICES, default=1.2)

    def calculate_bmr(self):
        if self.gender == 'male':
            return (10 * self.weight) + (6.25 * self.height) - (5 * self.age) + 5
        else:
            return (10 * self.weight) + (6.25 * self.height) - (5 * self.age) - 161

    def daily_calories(self):
        return self.calculate_bmr() * self.activity_level

    def daily_macros(self, goal="maintain"):
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
