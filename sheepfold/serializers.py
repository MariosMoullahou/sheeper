from rest_framework import serializers
from .models import Milk,Sheep,BirthEvent,CalendarEvent

class MilkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Milk
        fields = ["id","sheep","date","milk"]
        extra_kwargs = {
            'date': {'read_only': True}
        }

class CreateSheep(serializers.ModelSerializer):
    class Meta:
        model = Sheep 
        fieds = '__all__'

class SheepData(serializers.ModelSerializer):
    class Meta:
        model = Sheep
        fields = '__all__'

class BirthEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = BirthEvent
        fields = ["earing","mother","date","lambs"]

class CalendarEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalendarEvent
        fields = '__all__'