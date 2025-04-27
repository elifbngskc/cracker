from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from tracker.models import Profile


class UserRegisterForm(UserCreationForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['age', 'weight', 'height', 'gender', 'activity_level']
        widgets = {
            'gender': forms.Select(choices=Profile._meta.get_field('gender').choices),
            'activity_level': forms.Select(choices=Profile._meta.get_field('activity_level').choices),
        }
