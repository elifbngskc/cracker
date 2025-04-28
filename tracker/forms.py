from django import forms
from django.contrib.auth.models import User
from .models import Profile

GOAL_CHOICES = [
    ('maintain', 'Maintain'),
    ('lose', 'Lose weight'),
    ('gain', 'Gain weight')
]

class ProfileForm(forms.ModelForm):
    goal = forms.ChoiceField(choices=GOAL_CHOICES, required=False, initial='maintain')

    class Meta:
        model = Profile
        fields = ['age', 'weight', 'height', 'gender', 'activity_level', 'goal']
        widgets = {
            'gender': forms.Select(choices=Profile._meta.get_field('gender').choices),
            'activity_level': forms.Select(choices=Profile._meta.get_field('activity_level').choices),
        }
