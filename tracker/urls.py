from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('mealdetail/', views.mealdetail, name='mealdetail'),
    path('contact/', views.contact, name='contact'),
    path('form/', views.get_calories, name='get_calories'),
    path('cal_calc', views.calc, name='calc')
]
