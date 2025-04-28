from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import UserRegisterForm
from tracker.models import Profile


def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Your account has been created! You are now able to log in')
            return redirect('login')
    else:
        form = UserRegisterForm()
    return render(request, 'users/register.html', {'form': form})


@login_required
def profile(request):
    profile = get_object_or_404(Profile, user=request.user)

    context = {
        'profile': profile,
        'daily_calories': round(profile.daily_calories()),
        'daily_macros': profile.daily_macros(),}
    
    return render(request, 'users/profile.html', context)