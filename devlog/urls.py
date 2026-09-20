from django.urls import path

from . import views

app_name = 'devlog'

urlpatterns = [
    path('changelog/', views.changelog, name='changelog'),
]
