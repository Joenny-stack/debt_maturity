from django.urls import path
from . import views
from .views import financials_view

urlpatterns = [
    path('', financials_view, name='financials_view'),
]

