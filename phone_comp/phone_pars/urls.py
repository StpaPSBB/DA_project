from .views import PhoneModelParserAPI
from django.urls import path

urlpatterns=[
    path('phone_pars/', PhoneModelParserAPI.as_view()),
]