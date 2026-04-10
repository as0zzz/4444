from django import forms
from .models import UserData
from .models import Event

class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserData
        fields = ['event_phone', 'fio', 'event_email', 'event_name', 'field_of_work', 'organization_of_work', 'event_description']
        widgets = {
            'event_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'fio': forms.TextInput(attrs={'class': 'form-control'}),
            'event_email': forms.TextInput(attrs={'class': 'form-control'}),
            'event_name': forms.TextInput(attrs={'class': 'form-control'}),
            'field_of_work': forms.TextInput(attrs={'class': 'form-control'}),
            'organization_of_work': forms.TextInput(attrs={'class': 'form-control'}),
            'event_description': forms.TextInput(attrs={'class': 'form-control'}),
        }




class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['event_name', 'event_phone', 'event_email', 'fio', 'field_of_work', 'organization_of_work', 'event_description']
        widgets = {
            'event_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Название мероприятия'}),
            'event_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Телефон'}),
            'event_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
            'fio': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ФИО'}),
            'field_of_work': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Сфера деятельности'}),
            'organization_of_work': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Организация'}),
            'event_description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Описание', 'rows': 5}),
        }
