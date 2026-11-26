import random
import time
from django.conf import settings
from django.core.mail import send_mail
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User, Group
from django.db import transaction
from django.db.models import Sum

from .models import Stock, Patient, Donor, BLOOD_GROUP_CHOICES
from .forms import (
    StockForm, PatientUserForm, PatientForm, DonorUserForm, DonorForm,
    PatientEmailOTPForm, OTPVerificationForm
)


def is_admin(user):
    """Check if the user is staff or superuser (admin)."""
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def is_patient(user):
    """Check if the user is authenticated and has a patient profile or belongs to PATIENT group."""
    return user.is_authenticated and (
        hasattr(user, 'patient_profile') or user.groups.filter(name='PATIENT').exists()
    )


def is_donor(user):
    """Check if the user is authenticated and has a donor profile or belongs to DONOR group."""
    return user.is_authenticated and (
        hasattr(user, 'donor_profile') or user.groups.filter(name='DONOR').exists()
    )




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
                    user: User = user_form.save(commit=False)
                    user.set_password(user_form.cleaned_data['password'])
                    user.save()

                    # 2. Assign to PATIENT group
                    patient_group, _ = Group.objects.get_or_create(name='PATIENT')
                    user.groups.add(patient_group)

                    # 3. Create and save Patient instance linked to User into DB
                    patient: Patient = patient_form.save(commit=False)
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
                    user: User = user_form.save(commit=False)
                    user.set_password(user_form.cleaned_data['password'])
                    user.save()

                    # 2. Assign to DONOR group
                    donor_group, _ = Group.objects.get_or_create(name='DONOR')
                    user.groups.add(donor_group)

                    # 3. Create and save Donor instance linked to User into DB
                    donor: Donor = donor_form.save(commit=False)
                    donor.user = user
                    donor.save()

                messages.success(request, f'Registration successful for donor {user.username}! Thank you for registering to save lives. You can now log in.')
                return redirect('donor_login')
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
        if is_patient(request.user):
            return redirect('patient_dashboard')
        elif request.user.is_staff or request.user.is_superuser:
            return redirect('stock_list')
        return redirect('home')

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


# ==========================================
# Patient Email OTP Authentication Views (Tasks 1, 2 & 3)
# ==========================================
def patient_request_otp(request):
    """
    Task 1: Create a form where patients can enter their registered email to receive OTP.
    Task 2: Generate random OTP and send it to the patient's email using Django's email backend.
    """
    if request.user.is_authenticated and is_patient(request.user):
        return redirect('patient_dashboard')

    if request.method == 'POST':
        form = PatientEmailOTPForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user: User = form.user

            # Task 2: Generate random 6-digit OTP
            otp = f"{random.randint(100000, 999999)}"

            # Store OTP and metadata in session (10 minutes validity)
            request.session['patient_otp'] = str(otp)
            request.session['otp_user_id'] = user.id
            request.session['otp_email'] = email
            request.session['otp_timestamp'] = time.time()

            # Task 2: Send OTP to patient's email using Django's email backend
            subject = 'Blood Bank System - Your Login Verification OTP'
            message = (
                f"Hello {user.first_name or user.username},\n\n"
                f"Your One-Time Password (OTP) for patient login verification is:\n\n"
                f"   {otp}\n\n"
                f"This code will expire in 10 minutes.\n"
                f"If you did not request this OTP, please ignore this email.\n\n"
                f"Best regards,\nBlood Bank System Team"
            )
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'bloodbank@example.com')
            try:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=from_email,
                    recipient_list=[email],
                    fail_silently=False,
                )
                messages.success(request, f'A 6-digit OTP has been sent to {email}. Please enter it below.')
                return redirect('patient_verify_otp')
            except Exception as e:
                messages.error(request, f'Unable to send OTP email: {str(e)}')
        else:
            messages.error(request, 'Please check your email address and try again.')
    else:
        form = PatientEmailOTPForm()

    return render(request, 'blood/patient_request_otp.html', {'form': form})


def patient_verify_otp(request):
    """
    Task 3: Create a verification page for entering OTP.
    - Validates entered OTP against session-stored OTP.
    - Enforces 10-minute expiry window.
    - Logs in verified patient and redirects to dashboard.
    """
    if request.user.is_authenticated and is_patient(request.user):
        return redirect('patient_dashboard')

    stored_otp = request.session.get('patient_otp')
    user_id = request.session.get('otp_user_id')
    otp_email = request.session.get('otp_email', '')

    # Redirect to request page if no active OTP session exists
    if not stored_otp or not user_id:
        messages.warning(request, 'Please enter your registered email to request an OTP code first.')
        return redirect('patient_request_otp')

    # Check expiration (10 minutes = 600 seconds)
    otp_timestamp = request.session.get('otp_timestamp', 0)
    if time.time() - otp_timestamp > 600:
        request.session.pop('patient_otp', None)
        request.session.pop('otp_user_id', None)
        request.session.pop('otp_email', None)
        request.session.pop('otp_timestamp', None)
        messages.error(request, 'Your OTP has expired. Please request a new verification code.')
        return redirect('patient_request_otp')

    if request.method == 'POST':
        form = OTPVerificationForm(request.POST)
        if form.is_valid():
            entered_otp = form.cleaned_data['otp']
            if entered_otp == stored_otp:
                try:
                    user = User.objects.get(id=user_id)
                    login(request, user)

                    # Initialize patient session
                    request.session['role'] = 'patient'
                    request.session['username'] = user.username
                    if hasattr(user, 'patient_profile'):
                        request.session['patient_id'] = user.patient_profile.id
                        request.session['bloodgroup'] = user.patient_profile.bloodgroup

                    # Clear OTP session keys
                    request.session.pop('patient_otp', None)
                    request.session.pop('otp_user_id', None)
                    request.session.pop('otp_email', None)
                    request.session.pop('otp_timestamp', None)

                    messages.success(request, f'Welcome back, {user.first_name or user.username}! OTP verified successfully.')
                    return redirect('patient_dashboard')
                except User.DoesNotExist:
                    messages.error(request, 'Patient account could not be found.')
                    return redirect('patient_request_otp')
            else:
                messages.error(request, 'Invalid OTP code. Please enter the correct 6-digit code sent to your email.')
        else:
            messages.error(request, 'Please enter a valid 6-digit OTP code.')
    else:
        form = OTPVerificationForm()

    context = {
        'form': form,
        'email': otp_email,
    }
    return render(request, 'blood/patient_verify_otp.html', context)



@login_required(login_url='patient_login')
def patient_dashboard(request):
    """
    Task: Secure patient dashboard so only authenticated patients can access it.
    - Enforces authentication via @login_required(login_url='patient_login').
    - Restricts access strictly to verified patients (blocks unauthenticated visitors & non-patients).
    - Redirects staff/admin or other non-patient users with an informative notification.
    - Displays active session metrics, patient medical information, live matching blood units,
      and transfusion compatibility guide.
    """
    # Security Check: Ensure authenticated user is actually a registered patient
    if not is_patient(request.user):
        messages.error(request, 'Access denied. The patient dashboard is only accessible to registered patients.')
        if request.user.is_staff or request.user.is_superuser:
            return redirect('stock_list')
        return redirect('home')

    patient = getattr(request.user, 'patient_profile', None)
    if not patient:
        messages.warning(request, 'Patient profile details not found. Please complete your registration.')
        return redirect('patient_register')

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


# ==========================================
# Donor Authentication & Dashboard Views (Tasks 1, 2 & 3)
# ==========================================
def donor_login_view(request):
    """
    Task 1: Implement donor login functionality.
    - Validates donor credentials via AuthenticationForm.
    - Sets up session attributes ('role': 'donor', 'donor_id', 'bloodgroup').
    - Authenticates and logs in donor using Django's login().
    - Redirects to donor_dashboard on success.
    """
    if request.user.is_authenticated:
        if is_donor(request.user):
            return redirect('donor_dashboard')
        elif is_patient(request.user):
            return redirect('patient_dashboard')
        elif is_admin(request.user):
            return redirect('stock_list')
        return redirect('home')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user: User = form.get_user()
            login(request, user)

            # Session handling: Store donor session data
            request.session['role'] = 'donor'
            request.session['username'] = user.username
            if hasattr(user, 'donor_profile'):
                request.session['donor_id'] = user.donor_profile.id
                request.session['bloodgroup'] = user.donor_profile.bloodgroup

            messages.success(request, f'Welcome back, {user.first_name or user.username}!')
            return redirect('donor_dashboard')
        else:
            messages.error(request, 'Invalid username or password. Please try again.')
    else:
        form = AuthenticationForm()

    return render(request, 'blood/login.html', {
        'form': form,
        'title': 'Donor Login',
        'is_donor': True,
        'is_admin': False
    })


def donor_logout_view(request):
    """
    Task 1: Implement donor logout functionality.
    - Clears all session keys and flushes session data.
    - Logs out user via Django's logout().
    - Redirects with a friendly notification message.
    """
    request.session.flush()
    logout(request)
    messages.info(request, 'You have been successfully logged out.')
    return redirect('donor_login')


@login_required(login_url='donor_login')
def donor_dashboard(request):
    """
    Task 2 & 3: Create a donor dashboard view post-login & restrict access to logged-in donor users only.
    - Enforces authentication via @login_required(login_url='donor_login').
    - Restricts access strictly to verified donors (blocks unauthenticated visitors & non-donors).
    - Redirects staff/admin or patient users with an informative notification.
    - Displays active session metrics, donor profile, live bank stock, and blood donation impact compatibility guide.
    """
    # Task 3 Security Check: Ensure authenticated user is actually a registered donor
    if not is_donor(request.user):
        messages.error(request, 'Access denied. The donor dashboard is only accessible to registered donors.')
        if is_admin(request.user):
            return redirect('stock_list')
        elif is_patient(request.user):
            return redirect('patient_dashboard')
        return redirect('home')

    donor = getattr(request.user, 'donor_profile', None)
    if not donor:
        messages.warning(request, 'Donor profile details not found. Please complete your registration.')
        return redirect('donor_register')

    # Blood donation recipient compatibility map (who can RECEIVE this donor's blood)
    donation_map = {
        'O-': ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'], # Universal Donor
        'O+': ['O+', 'A+', 'B+', 'AB+'],
        'B-': ['B+', 'B-', 'AB+', 'AB-'],
        'B+': ['B+', 'AB+'],
        'A-': ['A+', 'A-', 'AB+', 'AB-'],
        'A+': ['A+', 'AB+'],
        'AB-': ['AB+', 'AB-'],
        'AB+': ['AB+'],
    }

    matching_stock = Stock.objects.filter(bloodgroup=donor.bloodgroup).first()
    can_donate_to = donation_map.get(donor.bloodgroup, [])
    total_stock = Stock.objects.aggregate(Sum('unit'))['unit__sum'] or 0

    context = {
        'donor': donor,
        'user': request.user,
        'matching_stock': matching_stock,
        'can_donate_to': can_donate_to,
        'total_stock': total_stock,
        'session_role': request.session.get('role', 'donor'),
    }
    return render(request, 'blood/donor_dashboard.html', context)




def logout_view(request):
    """General logout redirecting to home."""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('home')
