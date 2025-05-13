from rest_framework import serializers
from .models import *

class PhoneDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhoneData
        fields = ['model', 'data']