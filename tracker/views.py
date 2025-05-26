from django.shortcuts import render, redirect, get_object_or_404
from .forms import ProfileForm, EatenFoodForm
from django.contrib.auth.decorators import login_required
import requests
from .models import FoodItem, Profile, EatenFood
from django.http import JsonResponse
from .utils import query_ollama
import redis
import json
from django.conf import settings
from collections import defaultdict
from datetime import date

@login_required
def home(request):
    today = date.today()
    meal_types = ['breakfast', 'lunch', 'dinner', 'snack']
    meal_data = {}

    for meal in meal_types:
        foods = EatenFood.objects.filter(user=request.user, meal_type=meal, date=today)
        total = {
            'calories': sum(f.total_nutrients()['calories'] for f in foods),
            'carbohydrates': sum(f.total_nutrients()['carbohydrates'] for f in foods),
            'fats': sum(f.total_nutrients()['fats'] for f in foods),
            'proteins': sum(f.total_nutrients()['proteins'] for f in foods),
            'fiber': sum(f.total_nutrients()['fiber'] for f in foods),
        }
        meal_data[meal] = {
            'foods': foods,
            'total': total
        }

    # Day total
    day_total = {
        'calories': 0, 'carbohydrates': 0, 'fats': 0, 'proteins': 0, 'fiber': 0
    }
    for data in meal_data.values():
        for key in day_total:
            day_total[key] += data['total'][key]

    # Get needed and remaining calories
    needed_calories = 0
    remaining_calories = 0
    try:
        profile = Profile.objects.get(user=request.user)
        needed_calories = profile.daily_calories()  # <-- fix here
        remaining_calories = needed_calories - day_total['calories']
    except Profile.DoesNotExist:
        pass

    return render(request, "tracker/home.html", {
        'meal_data': meal_data,
        'day_total': day_total,
        'needed_calories': needed_calories,
        'remaining_calories': remaining_calories
    })

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
r = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=1
)

def get_calories(request):
    food_info = None
    error = None

    if request.method == 'POST':
        food_name = request.POST.get('food', '').strip().lower()
        print(f"Received food_name: {food_name}")

        redis_key = f"calories:{food_name}"
        cached_data = r.get(redis_key)

        if cached_data:
            print("Data found in Redis:", cached_data)
            try:
                data = json.loads(cached_data)
                food_info = FoodItem(
                    name=data.get('name'),
                    calories=data.get('calories'),
                    carbohydrates=data.get('carbohydrates'),
                    fats=data.get('fats'),
                    proteins=data.get('proteins'),
                    fiber=data.get('fiber')
                )
            except Exception as e:
                error = f"Redis data couldn't be processed: {e}"
        else:
            print("Data couldn't be found, making API call.")
            try:
                food = FoodItem.objects.get(name__iexact=food_name)
                food_info = food
            except FoodItem.DoesNotExist:
                url = f"https://api.nal.usda.gov/fdc/v1/foods/search?query={food_name}&api_key={USDA_API_KEY}"
                response = requests.get(url)

                if response.status_code == 200:
                    data = response.json()
                    try:
                        first_result = data['foods'][0]
                        nutrients = {
                            nutrient['nutrientName']: nutrient['value']
                            for nutrient in first_result['foodNutrients']
                        }

                        food = FoodItem.objects.create(
                            name=food_name,
                            calories=nutrients.get('Energy'),
                            carbohydrates=nutrients.get('Carbohydrate, by difference'),
                            fats=nutrients.get('Total lipid (fat)'),
                            proteins=nutrients.get('Protein'),
                            fiber=nutrients.get('Fiber, total dietary')
                        )
                        food_info = food

                        # Save on redis for 15 days
                        try:
                            r.setex(redis_key, 60 * 60 * 24 * 15, json.dumps({
                                "name": food.name,
                                "calories": food.calories,
                                "carbohydrates": food.carbohydrates,
                                "fats": food.fats,
                                "proteins": food.proteins,
                                "fiber": food.fiber
                            }))
                            print(f"Data cached in Redis with key {redis_key}")
                        except Exception as e:
                            print(f"Redis setex error: {e}")

                    except (IndexError, KeyError):
                        error = 'Food not found in API.'
                else:
                    error = 'Error fetching from API.'

    return render(request, 'tracker/food_form.html', {'food_info': food_info, 'error': error})

@login_required
def get_llama_response(request):
    try:
        profile = Profile.objects.get(user=request.user)
    except Profile.DoesNotExist:
        return JsonResponse({"error": "Profile not found."}, status=404)

    age = profile.age
    weight = profile.weight
    height = profile.height
    gender = profile.gender
    activity_level = dict(Profile.ACTIVITY_LEVEL_CHOICES).get(profile.activity_level, "Unknown")
    goal = profile.goal

    prompt = (
        f"I have a user with the following profile:\n"
        f"- Age: {age}\n"
        f"- Weight: {weight} kg\n"
        f"- Height: {height} cm\n"
        f"- Gender: {gender}\n"
        f"- Activity level: {activity_level}\n"
        f"- Goal: {goal}\n\n"
        f"Please suggest a healthy meal suitable for this user and tell me its approximate calorie content. "
        f"Do NOT add this meal to any meal log or database; just provide the information."
    )

    result = query_ollama(prompt)

    return JsonResponse({"response": result})

@login_required
def add_eaten_food(request):
    if request.method == 'POST':
        form = EatenFoodForm(request.POST)
        if form.is_valid():
            eaten = form.save(commit=False)
            eaten.user = request.user
            eaten.save()
            return redirect('daily_summary')
    else:
        form = EatenFoodForm()
    return render(request, 'tracker/add_eaten_food.html', {'form': form})

@login_required
def daily_summary(request):
    today = date.today()
    foods = EatenFood.objects.filter(user=request.user, date=today)

    summary = defaultdict(lambda: {
        'calories': 0, 'carbohydrates': 0, 'fats': 0, 'proteins': 0, 'fiber': 0
    })

    for food in foods:
        nutrients = food.total_nutrients()
        meal = food.meal_type
        for key in summary[meal]:
            summary[meal][key] += nutrients[key]

    total = {key: sum(meal[key] for meal in summary.values()) for key in summary['breakfast']}

    return render(request, 'tracker/daily_summary.html', {
        'summary': dict(summary),
        'total': total
    })

@login_required
def meal_view(request, meal_type):
    today = date.today()
    foods = EatenFood.objects.filter(user=request.user, meal_type=meal_type, date=today)

    total = {
        'calories': sum(f.total_nutrients()['calories'] for f in foods),
        'carbohydrates': sum(f.total_nutrients()['carbohydrates'] for f in foods),
        'fats': sum(f.total_nutrients()['fats'] for f in foods),
        'proteins': sum(f.total_nutrients()['proteins'] for f in foods),
        'fiber': sum(f.total_nutrients()['fiber'] for f in foods),
    }

    return render(request, 'tracker/meal_view.html', {
        'meal_type': meal_type,
        'foods': foods,
        'total': total
    })

@login_required
def add_food_to_meal(request, meal_type):
    search_results = None
    if request.method == 'POST':
        if 'search' in request.POST:
            food_name = request.POST.get('food_name').strip().lower()
            search_results = FoodItem.objects.filter(name__icontains=food_name)
        elif 'add_food' in request.POST:
            food_id = request.POST.get('food_id')
            quantity = float(request.POST.get('quantity', 1))
            food = get_object_or_404(FoodItem, id=food_id)

            today = date.today()
            existing_entry = EatenFood.objects.filter(
                user=request.user,
                food=food,
                meal_type=meal_type,
                date=today
            ).first()

            if existing_entry:
                # Add to existing quantity
                existing_entry.quantity += quantity
                existing_entry.save()
            else:
                # Create new entry
                EatenFood.objects.create(
                    user=request.user,
                    food=food,
                    meal_type=meal_type,
                    quantity=quantity,
                    date=today
                )

            return redirect('tracker:meal_view', meal_type=meal_type)

    return render(request, 'tracker/add_food_to_meal.html', {
        'meal_type': meal_type,
        'search_results': search_results
    })
