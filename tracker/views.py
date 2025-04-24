from django.shortcuts import render

def home(request):
    return render(request, "tracker/home.html")

def contact(request):
    return render(request, "tracker/contact.html")

def mealdetail(request):
    return render(request, "tracker/mealdetails.html")