from django.urls import path
from .views import *
from . import views

urlpatterns = [
    path('', views.open_1, name='open_1'),
    path('open_1/', views.open_1, name='open_1'),
    path('logout/', views.logout_view, name='logout'),  # Выход


    path('open_2/', views.open_2, name='open_2'),
    path('open_3/', views.open_3, name='open_3'),
    path('home/', views.home, name='home'),
    path('profile/', views.profile, name='profile'),
    path('form_1/', views.form_1, name='form_1'),
    path('form_2/', views.form_2, name='form_2'),
    path('profile_test/', views.profile_test, name='profile_test'),
]