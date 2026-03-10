from django import forms
from .models import Sheep,BirthEvent,Milk

class SheepForm(forms.ModelForm):
    class Meta:
        model = Sheep
        fields = ["earing", "gender"]

class SheepingForm(forms.ModelForm):
    class Meta:
        model = BirthEvent
        fields = ["mother","date","notes","lambs"]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'lambs': forms.SelectMultiple(attrs={'size': '10'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Optional: filter lambs to only show sheep without a mother
        self.fields['lambs'].queryset = Sheep.objects.filter(mother__isnull=True)

class MilkForm(forms.ModelForm):
    class Meta:
        model = Milk
        fields = '__all__'