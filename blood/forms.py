from django import forms
from django.contrib.auth.models import User
from .models import Stock, Patient, BLOOD_GROUP_CHOICES


class StockForm(forms.ModelForm):
    """
    Form to allow admin to add or update blood stock entries.
    """
    class Meta:
        model = Stock
        fields = ['bloodgroup', 'unit']
        widgets = {
            'bloodgroup': forms.Select(attrs={
                'class': 'form-select form-select-lg',
                'required': 'required'
            }),
            'unit': forms.NumberInput(attrs={
                'class': 'form-control form-control-lg',
                'min': '0',
                'placeholder': 'Enter number of units (e.g. 10)',
                'required': 'required'
            }),
        }
        labels = {
            'bloodgroup': 'Blood Group',
            'unit': 'Blood Units (Bags)',
        }


class PatientUserForm(forms.ModelForm):
    """
    Collects User credentials and personal identity for patient registration.
    """
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Choose a strong password',
            'autocomplete': 'new-password'
        }),
        help_text='At least 8 characters recommended.'
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email', 'password']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name', 'required': 'required'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name', 'required': 'required'}),
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Unique Username', 'required': 'required'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'name@example.com', 'required': 'required'}),
        }


class PatientForm(forms.ModelForm):
    """
    Collects Patient medical and contact details (uses provided Patient model).
    """
    class Meta:
        model = Patient
        fields = ['age', 'bloodgroup', 'disease', 'doctorname', 'address', 'mobile', 'profile_pic']
        widgets = {
            'age': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Age', 'min': '1', 'max': '120', 'required': 'required'}),
            'bloodgroup': forms.Select(attrs={'class': 'form-select', 'required': 'required'}),
            'disease': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Reason / Disease (e.g., Anemia, Surgery)', 'required': 'required'}),
            'doctorname': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Consulting Doctor Name', 'required': 'required'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Current Residential Address', 'required': 'required'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '10-digit Mobile Number', 'required': 'required'}),
            'profile_pic': forms.FileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'bloodgroup': 'Blood Group Needed',
            'disease': 'Reason / Disease',
            'doctorname': "Doctor's Name",
            'mobile': 'Contact Mobile',
            'profile_pic': 'Profile Picture (Optional)'
        }
