from django.shortcuts import render, redirect
from .forms import ProfileForm
from django.contrib.auth.decorators import login_required

def home(request):
    return render(request, "tracker/home.html")

def contact(request):
    return render(request, "tracker/contact.html")

def mealdetail(request):
    return render(request, "tracker/mealdetails.html")

@login_required
def calc(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            profile.save()
            return redirect('profile')
    else:
        form = ProfileForm()
    return render(request, 'users/profile.html', {'form': form}) 