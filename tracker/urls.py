from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('weekly-progress/', views.weekly_progress, name='weekly_progress'),
    path('contact/', views.contact, name='contact'),
    path('form/', views.get_calories, name='get_calories'),
    path('cal_calc', views.calc, name='calc'),
    path('meals/<str:meal_type>/', views.meal_view, name='meal_view'),
    path('meals/<str:meal_type>/add/', views.add_food_to_meal, name='add_food_to_meal'),
]
