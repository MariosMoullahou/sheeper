from django import forms
from django.core.exceptions import ValidationError
from .models import Sheep, BirthEvent, Milk


class SheepForm(forms.ModelForm):
    class Meta:
        model = Sheep
        fields = ["earing", "gender", "birthdate", "mother", "father", "is_active"]
        widgets = {
            'birthdate': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_mother(self):
        mother = self.cleaned_data.get('mother')
        if mother and mother.gender == 'M':
            raise ValidationError('Mother must be female.')
        return mother

    def clean_father(self):
        father = self.cleaned_data.get('father')
        if father and father.gender == 'F':
            raise ValidationError('Father must be male.')
        return father


class SheepingForm(forms.ModelForm):
    class Meta:
        model = BirthEvent
        fields = ["mother", "date", "notes", "lambs"]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'lambs': forms.SelectMultiple(attrs={'size': '10'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, farm=None, **kwargs):
        super().__init__(*args, **kwargs)
        if farm is not None:
            self.fields['mother'].queryset = Sheep.objects.filter(
                farm=farm, gender='F',
            )
            self.fields['lambs'].queryset = Sheep.objects.filter(
                farm=farm, mother__isnull=True,
            )

    def clean_mother(self):
        mother = self.cleaned_data.get('mother')
        if mother and mother.gender == 'M':
            raise ValidationError('Mother must be female.')
        return mother


class MilkForm(forms.ModelForm):
    class Meta:
        model = Milk
        fields = ["sheep", "date", "milk", "is_active"]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, farm=None, **kwargs):
        super().__init__(*args, **kwargs)
        if farm is not None:
            self.fields['sheep'].queryset = Sheep.objects.filter(farm=farm).exclude(gender='M')
