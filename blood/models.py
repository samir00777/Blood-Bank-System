from django.db import models
from django.contrib.auth.models import User

BLOOD_GROUP_CHOICES = [
    ('A+', 'A+'),
    ('A-', 'A-'),
    ('B+', 'B+'),
    ('B-', 'B-'),
    ('AB+', 'AB+'),
    ('AB-', 'AB-'),
    ('O+', 'O+'),
    ('O-', 'O-'),
]


class Stock(models.Model):
    """
    Stock model with fields: bloodgroup and unit
    Tracks current blood units in inventory.
    """
    bloodgroup = models.CharField(max_length=10, choices=BLOOD_GROUP_CHOICES, unique=True)
    unit = models.PositiveIntegerField(default=0)

    objects = models.Manager()

    class Meta:
        ordering = ['bloodgroup']
        verbose_name = 'Blood Stock'
        verbose_name_plural = 'Blood Stocks'

    def __str__(self):
        return f"{self.bloodgroup} ({self.unit} Units)"


class Patient(models.Model):
    """
    Patient model linked to User model.
    Stores medical and contact details of the patient.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='patient_profile')
    profile_pic = models.ImageField(upload_to='profile_pic/Patient/', null=True, blank=True)
    age = models.PositiveIntegerField()
    bloodgroup = models.CharField(max_length=10, choices=BLOOD_GROUP_CHOICES)
    disease = models.CharField(max_length=100)
    doctorname = models.CharField(max_length=50)
    address = models.CharField(max_length=200)
    mobile = models.CharField(max_length=20)

    objects = models.Manager()

    @property
    def get_name(self):
        return f"{self.user.first_name} {self.user.last_name}".strip() or self.user.username

    @property
    def get_instance(self):
        return self

    def __str__(self):
        return f"{self.get_name} ({self.bloodgroup})"


class Donor(models.Model):
    """
    Donor model linked to User model.
    Stores contact and blood donation details of the donor.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='donor_profile')
    profile_pic = models.ImageField(upload_to='profile_pic/Donor/', null=True, blank=True)
    bloodgroup = models.CharField(max_length=10, choices=BLOOD_GROUP_CHOICES)
    address = models.CharField(max_length=200)
    mobile = models.CharField(max_length=20)

    objects = models.Manager()

    @property
    def get_name(self):
        return f"{self.user.first_name} {self.user.last_name}".strip() or self.user.username

    @property
    def get_instance(self):
        return self

    def __str__(self):
        return f"{self.get_name} ({self.bloodgroup})"

