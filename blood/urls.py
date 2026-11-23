from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    
    # Blood Stock URLs (Admin only)
    path('stocks/', views.stock_list, name='stock_list'),                   # Task 5
    path('stocks/add/', views.add_stock, name='add_stock'),                 # Task 6
    path('stocks/update/<int:pk>/', views.update_stock, name='update_stock'),# Task 1
    path('stocks/delete/<int:pk>/', views.delete_stock, name='delete_stock'),# Task 1

    # Patient Registration (User + Patient)
    path('patient/register/', views.patient_register, name='patient_register'), # Task 3

    # Authentication & Dashboard (Django Auth)
    path('admin-login/', views.admin_login_view, name='admin_login'),
    path('patient-login/', views.patient_login_view, name='patient_login'),
    path('patient-logout/', views.patient_logout_view, name='patient_logout'),
    path('patient-dashboard/', views.patient_dashboard, name='patient_dashboard'),
    path('logout/', views.logout_view, name='logout'),
]
