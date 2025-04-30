from django.shortcuts import render, redirect
from .forms import ProfileForm
from django.contrib.auth.decorators import login_required
import requests
from .models import FoodItem, Profile
from django.http import JsonResponse
from .utils import query_ollama

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
    return render(request, 'tracker/calorie_calc.html', {'form': form}) 

USDA_API_KEY = 'L3nkiRdZQeKTqXivIctEq22hyBP2eV8wE1CSY2cJ'

def get_calories(request):
    food_info = None
    error = None

    if request.method == 'POST':
        food_name = request.POST.get('food')

        try:
            food = FoodItem.objects.get(name__iexact=food_name)
            food_info = food

        except FoodItem.DoesNotExist:
            # API'den veri çek
            url = f"https://api.nal.usda.gov/fdc/v1/foods/search?query={food_name}&api_key={USDA_API_KEY}"
            response = requests.get(url)

            if response.status_code == 200:
                data = response.json()
                try:
                    first_result = data['foods'][0]
                    nutrients = {nutrient['nutrientName']: nutrient['value'] for nutrient in first_result['foodNutrients']}
                    
                    food = FoodItem.objects.create(
                        name=food_name,
                        calories=nutrients.get('Energy'),
                        carbohydrates=nutrients.get('Carbohydrate, by difference'),
                        fats=nutrients.get('Total lipid (fat)'),
                        proteins=nutrients.get('Protein'),
                        fiber=nutrients.get('Fiber, total dietary')
                    )
                    food_info = food

                except (IndexError, KeyError):
                    error = 'Food not found in API.'
            else:
                error = 'Error fetching from API.'

    return render(request, 'tracker/food_form.html', {'food_info': food_info, 'error': error})

def get_llama_response(request):
    prompt = "Can you calculate my breakfast calories"
    result = query_ollama(prompt)
    return JsonResponse({"response": result}) 