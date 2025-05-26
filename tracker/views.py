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
from datetime import date, timedelta
from django.utils import timezone

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

        # Redis anahtarı için lowercase api_name'i kullanalım
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
                # Burada da veritabanında tam isim eşleşmesi değil,
                # lowercase ile daha esnek arama yapılabilir
                food = FoodItem.objects.filter(name__iexact=food_name).first()
                if food:
                    food_info = food
                    # Redis'e kaydet, api_name üzerinden değil ama burada eklenebilir
                    redis_key = f"calories:{food.name.lower()}"
                    try:
                        r.setex(redis_key, 60 * 60 * 24 * 15, json.dumps({
                            "name": food.name,
                            "calories": food.calories,
                            "carbohydrates": food.carbohydrates,
                            "fats": food.fats,
                            "proteins": food.proteins,
                            "fiber": food.fiber
                        }))
                    except Exception as e:
                        print(f"Redis setex error: {e}")

                else:
                    url = f"https://api.nal.usda.gov/fdc/v1/foods/search?query={food_name}&api_key={USDA_API_KEY}"
                    response = requests.get(url)

                    if response.status_code == 200:
                        data = response.json()
                        try:
                            first_result = data['foods'][0]
                            nutrients = {
                                nutrient['nutrientName']: nutrient['value']
                                for nutrient in first_result.get('foodNutrients', [])
                            }

                            api_name = first_result.get('description', food_name).title().strip()

                            food = FoodItem.objects.create(
                                name=api_name,
                                calories=nutrients.get('Energy'),
                                carbohydrates=nutrients.get('Carbohydrate, by difference'),
                                fats=nutrients.get('Total lipid (fat)'),
                                proteins=nutrients.get('Protein'),
                                fiber=nutrients.get('Fiber, total dietary')
                            )
                            food_info = food

                            # Redis'e api_name ile kaydet
                            redis_key = f"calories:{api_name.lower()}"
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

            except Exception as e:
                error = str(e)

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
    error = None

    if request.method == 'POST':
        if 'search' in request.POST:
            food_name = request.POST.get('food_name').strip().lower()

            # Veritabanında arama
            search_results = FoodItem.objects.filter(name__icontains=food_name)

            # Tam eşleşme yoksa API'den veriyi çek
            exact_match = search_results.filter(name__iexact=food_name).exists()
            if not exact_match:
                url = f"https://api.nal.usda.gov/fdc/v1/foods/search?query={food_name}&api_key={USDA_API_KEY}"
                response = requests.get(url)

                if response.status_code == 200:
                    data = response.json()
                    try:
                        first_result = data['foods'][0]
                        nutrients = {
                            nutrient['nutrientName']: nutrient['value']
                            for nutrient in first_result.get('foodNutrients', [])
                        }

                        # API'den gelen isim
                        api_name = first_result.get('description', food_name).title().strip()

                        # Bu isim veritabanında zaten var mı?
                        existing_food = FoodItem.objects.filter(name__iexact=api_name).first()
                        if existing_food:
                            food = existing_food
                        else:
                            food = FoodItem.objects.create(
                                name=api_name,
                                calories=nutrients.get('Energy'),
                                carbohydrates=nutrients.get('Carbohydrate, by difference'),
                                fats=nutrients.get('Total lipid (fat)'),
                                proteins=nutrients.get('Protein'),
                                fiber=nutrients.get('Fiber, total dietary')
                            )

                            # Redis'e kaydet (yalnızca yeni oluşturulduysa)
                            redis_key = f"calories:{api_name.lower()}"
                            try:
                                r.setex(redis_key, 60 * 60 * 24 * 15, json.dumps({
                                    "name": food.name,
                                    "calories": food.calories,
                                    "carbohydrates": food.carbohydrates,
                                    "fats": food.fats,
                                    "proteins": food.proteins,
                                    "fiber": food.fiber
                                }))
                            except Exception as e:
                                print(f"Redis setex error: {e}")

                        search_results = [food]

                    except (IndexError, KeyError):
                        error = 'Yiyecek API\'de bulunamadı.'
                else:
                    error = 'API\'den veri çekilirken hata oluştu.'

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
                existing_entry.quantity += quantity
                existing_entry.save()
            else:
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
        'search_results': search_results,
        'error': error
    })




@login_required
def weekly_progress(request):
    profile = request.user.profile
    today = timezone.now().date()
    week_start = today - timedelta(days=6)

    # 👉 Ask for weight first, unless skipped
    if request.method == 'GET' and 'skip_weight' not in request.GET and 'weight' not in request.GET:
        return render(request, 'tracker/weight.html')

    weight_msg = None
    if request.method == 'GET' and 'weight' in request.GET:
        try:
            new_weight = float(request.GET.get("weight"))
            old_weight = profile.weight
            diff = new_weight - old_weight
            profile.weight = new_weight
            profile.save()
            if abs(diff) < 0.1:
                weight_msg = "Your weight stayed the same. Even so, fat loss and muscle gain may still be happening! Next week, focus on sleep and hydration."
            elif diff > 0:
                weight_msg = "You gained weight, but you’re still on track! Gains can come from muscles or fluctuations. Stay consistent and trust the process."
            else:
                weight_msg = "Congratulations! You lost weight. Keep up the consistent effort—you're doing amazing!"
        except ValueError:
            messages.error(request, "Please enter a valid number.")
            return redirect("tracker:weekly_progress.html")

    # 🔽 Continue with progress analysis
    eaten_foods = EatenFood.objects.filter(user=request.user, date__range=(week_start, today))
    daily_goals = profile.daily_macros()
    daily_goal_cals = daily_goals["calories"]
    daily_fat_limit = daily_goals["fat_g"]

    day_summaries = {}
    goal_days = 0
    fat_warnings = 0
    total_cals = 0
    days_with_data = 0

    for day_offset in range(7):
        day = today - timedelta(days=day_offset)
        foods = eaten_foods.filter(date=day)
        if not foods.exists():
            continue

        day_total = sum(f.total_nutrients()['calories'] for f in foods)
        fat_total = sum(f.total_nutrients()['fats'] for f in foods)

        days_with_data += 1
        total_cals += day_total

        if abs(day_total - daily_goal_cals) < 150:
            goal_days += 1
        if fat_total > daily_fat_limit:
            fat_warnings += 1

        day_summaries[day] = {
            "calories": day_total,
            "fats": fat_total
        }

    # Summary messages
    if days_with_data > 0:
        avg_cals = total_cals / days_with_data
        cal_diff = avg_cals - daily_goal_cals
    else:
        avg_cals = 0
        cal_diff = 0

    if cal_diff < -500:
        cal_msg = "Please don’t starve yourself! We aim for consistency and health. Patience brings results. 🫶"
    elif cal_diff > 500:
        cal_msg = "Well… things happen, but my eyes are on you next week 👀👀"
    else:
        cal_msg = "You're mostly aligned with your calorie goals this week!"

    if goal_days >= 6:
        goal_streak = "Perfect! You hit your calorie goal most days! 🏆"
    elif goal_days >= 4:
        goal_streak = "Good! You're getting there. Keep it up! 💪"
    else:
        goal_streak = "I want to see you more in here! Let’s push harder next week 💥"

    if fat_warnings > 0:
        fat_msg = f"You went over your fat goal on {fat_warnings} day(s). Try to moderate fat sources next week!"
    else:
        fat_msg = None

    context = {
        "day_summaries": day_summaries,
        "weight_msg": weight_msg,
        "cal_msg": cal_msg,
        "goal_streak": goal_streak,
        "fat_msg": fat_msg,
        "days_with_data": days_with_data
    }

    return render(request, "tracker/weekly_progress.html", context)
