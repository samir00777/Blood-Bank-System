from django.contrib import admin
from .models import Stock, Patient, Donor


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('bloodgroup', 'unit')
    search_fields = ('bloodgroup',)
    ordering = ('bloodgroup',)


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('get_name', 'bloodgroup', 'age', 'mobile', 'doctorname', 'disease')
    list_filter = ('bloodgroup',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'mobile', 'doctorname')


@admin.register(Donor)
class DonorAdmin(admin.ModelAdmin):
    list_display = ('get_name', 'bloodgroup', 'mobile', 'address')
    list_filter = ('bloodgroup',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'mobile')

