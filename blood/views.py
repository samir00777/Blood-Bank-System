from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import Group
from django.db import transaction
from django.db.models import Sum

from .models import Stock, Patient, Donor, BLOOD_GROUP_CHOICES
from .forms import StockForm, PatientUserForm, PatientForm, DonorUserForm, DonorForm


def is_admin(user):
    """Check if the user is staff or superuser (admin)."""
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def home(request):
    """
    Landing page: Shows blood bank overview, summary statistics,
    and available blood units per group.
    """
    stocks = Stock.objects.all().order_by('bloodgroup')
    total_units = stocks.aggregate(Sum('unit'))['unit__sum'] or 0
    patient_count = Patient.objects.count()
    donor_count = Donor.objects.count()

    context = {
        'stocks': stocks,
        'total_units': total_units,
        'patient_count': patient_count,
        'donor_count': donor_count,
        'blood_groups': BLOOD_GROUP_CHOICES,
    }
    return render(request, 'home.html', context)


# ==========================================
# Task 5: Admin-only Stock List View (Table Format)
# ==========================================
@user_passes_test(is_admin, login_url='admin_login')
def stock_list(request):
    """
    Task 5: Implement a view to display current blood stock
    in a table format (admin only access).
    """
    stocks = Stock.objects.all().order_by('bloodgroup')
    total_units = stocks.aggregate(Sum('unit'))['unit__sum'] or 0

    context = {
        'stocks': stocks,
        'total_units': total_units,
    }
    return render(request, 'blood/stock_list.html', context)


# ==========================================
# Task 6: Admin Add New Blood Stock Entries
# ==========================================
@user_passes_test(is_admin, login_url='admin_login')
def add_stock(request):
    """
    Task 6: Create a form and view to allow admin to add new blood stock entries.
    If bloodgroup already exists, adds units to existing stock or sets new value.
    """
    if request.method == 'POST':
        form = StockForm(request.POST)
        if form.is_valid():
            bloodgroup = form.cleaned_data['bloodgroup']
            units_to_add = form.cleaned_data['unit']

            # If stock entry already exists for this blood group, update it
            stock_item, created = Stock.objects.get_or_create(
                bloodgroup=bloodgroup,
                defaults={'unit': units_to_add}
            )
            if not created:
                stock_item.unit += units_to_add
                stock_item.save()
                messages.success(request, f'Added {units_to_add} units to {bloodgroup}. Total is now {stock_item.unit} units.')
            else:
                messages.success(request, f'New stock created for {bloodgroup} with {units_to_add} units.')

            return redirect('stock_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = StockForm()

    return render(request, 'blood/stock_form.html', {
        'form': form,
        'action_title': 'Add New Blood Stock',
        'is_update': False
    })


# ==========================================
# Task 1: Update Existing Blood Stock Item
# ==========================================
@user_passes_test(is_admin, login_url='admin_login')
def update_stock(request, pk):
    """
    Task 1: Create update functionality for existing blood stock items.
    """
    stock_item = get_object_or_404(Stock, pk=pk)

    if request.method == 'POST':
        form = StockForm(request.POST, instance=stock_item)
        if form.is_valid():
            form.save()
            messages.success(request, f'Blood stock for {stock_item.bloodgroup} updated successfully to {stock_item.unit} units.')
            return redirect('stock_list')
        else:
            messages.error(request, 'Please correct the errors in the form.')
    else:
        form = StockForm(instance=stock_item)

    return render(request, 'blood/stock_form.html', {
        'form': form,
        'stock_item': stock_item,
        'action_title': f'Update Stock: {stock_item.bloodgroup}',
        'is_update': True
    })


# ==========================================
# Task 1: Delete Existing Blood Stock Item
# ==========================================
@user_passes_test(is_admin, login_url='admin_login')
def delete_stock(request, pk):
    """
    Task 1: Create delete functionality for existing blood stock items.
    """
    stock_item = get_object_or_404(Stock, pk=pk)

    if request.method == 'POST':
        bloodgroup = stock_item.bloodgroup
        stock_item.delete()
        messages.success(request, f'Stock item for {bloodgroup} has been deleted.')
        return redirect('stock_list')

    return render(request, 'blood/stock_confirm_delete.html', {'stock_item': stock_item})


# ==========================================
# Task: Patient Registration View with Form Validation & DB Save
# ==========================================
def patient_register(request):
    """
    Implement view logic to register patient with form validation and save to DB.
    - Validates User account credentials and Patient medical information.
    - Uses an atomic transaction to ensure both User and Patient are saved together.
    - Hashes password safely before database commit.
    - Assigns user to the PATIENT security group.
    - Persists Patient linked to User and redirects with success feedback.
    """
    if request.method == 'POST':
        user_form = PatientUserForm(request.POST)
        patient_form = PatientForm(request.POST, request.FILES)

        # Form Validation
        if user_form.is_valid() and patient_form.is_valid():
            try:
                with transaction.atomic():
                    # 1. Create and save User instance with hashed password
                    user = user_form.save(commit=False)
                    user.set_password(user_form.cleaned_data['password'])
                    user.save()

                    # 2. Assign to PATIENT group
                    patient_group, _ = Group.objects.get_or_create(name='PATIENT')
                    user.groups.add(patient_group)

                    # 3. Create and save Patient instance linked to User into DB
                    patient = patient_form.save(commit=False)
                    patient.user = user
                    patient.save()

                messages.success(request, f'Registration successful for {user.username}! You can now log in.')
                return redirect('patient_login')
            except Exception as e:
                messages.error(request, f'Database error while saving patient: {str(e)}')
        else:
            messages.error(request, 'Registration failed. Please correct the validation errors below.')
    else:
        user_form = PatientUserForm()
        patient_form = PatientForm()

    context = {
        'user_form': user_form,
        'patient_form': patient_form,
    }
    return render(request, 'blood/patient_register.html', context)


# ==========================================
# Task: Donor Registration View with Form Validation & DB Save
# ==========================================
def donor_register(request):
    """
    Build view to save donor details with validation.
    - Validates User account credentials (DonorUserForm) and Donor details (DonorForm).
    - Uses an atomic transaction to ensure both User and Donor are saved together.
    - Hashes password safely before database commit.
    - Assigns user to the DONOR security group.
    - Persists Donor linked to User into the database and redirects with success feedback.
    """
    if request.method == 'POST':
        user_form = DonorUserForm(request.POST)
        donor_form = DonorForm(request.POST, request.FILES)

        # Form Validation
        if user_form.is_valid() and donor_form.is_valid():
            try:
                with transaction.atomic():
                    # 1. Create and save User instance with hashed password
                    user = user_form.save(commit=False)
                    user.set_password(user_form.cleaned_data['password'])
                    user.save()

                    # 2. Assign to DONOR group
                    donor_group, _ = Group.objects.get_or_create(name='DONOR')
                    user.groups.add(donor_group)

                    # 3. Create and save Donor instance linked to User into DB
                    donor = donor_form.save(commit=False)
                    donor.user = user
                    donor.save()

                messages.success(request, f'Registration successful for donor {user.username}! Thank you for registering to save lives.')
                return redirect('home')
            except Exception as e:
                messages.error(request, f'Database error while saving donor: {str(e)}')
        else:
            messages.error(request, 'Registration failed. Please correct the validation errors below.')
    else:
        user_form = DonorUserForm()
        donor_form = DonorForm()

    context = {
        'user_form': user_form,
        'donor_form': donor_form,
    }
    return render(request, 'blood/donor_register.html', context)



# ==========================================
# Authentication Views
# ==========================================
def admin_login_view(request):
    """Login view specifically for administrators."""
    if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
        return redirect('stock_list')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.is_staff or user.is_superuser:
                login(request, user)
                messages.success(request, f'Welcome Admin {user.username}!')
                return redirect('stock_list')
            else:
                messages.error(request, 'Access denied. Only administrators can access stock management.')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()

    return render(request, 'blood/login.html', {'form': form, 'title': 'Admin Login', 'is_admin': True})


# ==========================================
# Patient Authentication & Dashboard Views (Django Auth + Session Handling)
# ==========================================
def patient_login_view(request):
    """
    Task: Implement login view for patients using Django auth with session handling.
    - Validates patient credentials via AuthenticationForm.
    - Sets up session attributes ('role': 'patient', 'patient_id', 'bloodgroup').
    - Authenticates and logs in patient using Django's login().
    - Redirects to patient_dashboard on success.
    """
    if request.user.is_authenticated:
        return redirect('patient_dashboard')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            # Session handling: Store patient session data
            request.session['role'] = 'patient'
            request.session['username'] = user.username
            if hasattr(user, 'patient_profile'):
                request.session['patient_id'] = user.patient_profile.id
                request.session['bloodgroup'] = user.patient_profile.bloodgroup

            messages.success(request, f'Welcome back, {user.first_name or user.username}!')
            return redirect('patient_dashboard')
        else:
            messages.error(request, 'Invalid username or password. Please try again.')
    else:
        form = AuthenticationForm()

    return render(request, 'blood/login.html', {
        'form': form,
        'title': 'Patient Login',
        'is_admin': False
    })


def patient_logout_view(request):
    """
    Task: Implement logout view for patients using Django auth.
    - Clears all session keys and flushes session data.
    - Logs out user via Django's logout().
    - Redirects with a friendly notification message.
    """
    request.session.flush()
    logout(request)
    messages.info(request, 'You have been successfully logged out.')
    return redirect('patient_login')


@login_required(login_url='patient_login')
def patient_dashboard(request):
    """
    Task: Create a dashboard/homepage for patients after login with session handling.
    - Validates active session and user authentication.
    - Retrieves patient medical profile and session state.
    - Displays available blood units matching the patient's blood type.
    - Computes compatible donor blood groups for emergency reference.
    """
    patient = getattr(request.user, 'patient_profile', None)

    # Blood compatibility reference map (recipient -> acceptable donor types)
    compatibility_map = {
        'A+': ['A+', 'A-', 'O+', 'O-'],
        'A-': ['A-', 'O-'],
        'B+': ['B+', 'B-', 'O+', 'O-'],
        'B-': ['B-', 'O-'],
        'AB+': ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'],
        'AB-': ['AB-', 'A-', 'B-', 'O-'],
        'O+': ['O+', 'O-'],
        'O-': ['O-'],
    }

    matching_stock = None
    compatible_groups = []
    if patient:
        matching_stock = Stock.objects.filter(bloodgroup=patient.bloodgroup).first()
        compatible_groups = compatibility_map.get(patient.bloodgroup, [])

    total_stock = Stock.objects.aggregate(Sum('unit'))['unit__sum'] or 0

    context = {
        'patient': patient,
        'user': request.user,
        'matching_stock': matching_stock,
        'compatible_groups': compatible_groups,
        'total_stock': total_stock,
        'session_role': request.session.get('role', 'patient'),
    }
    return render(request, 'blood/patient_dashboard.html', context)


def logout_view(request):
    """General logout redirecting to home."""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('home')
