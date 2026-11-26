from django.test import TestCase, Client
from django.urls import reverse
from django.core import mail
from django.contrib.auth.models import User
from blood.models import Stock, Patient, Donor
from blood.forms import DonorUserForm, DonorForm, PatientEmailOTPForm, OTPVerificationForm


class BloodBankSystemTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Admin user
        self.admin = User.objects.create_superuser(
            username='admin_test',
            password='testpassword123',
            email='admin@test.com'
        )
        # Regular user
        self.regular_user = User.objects.create_user(
            username='regular_test',
            password='testpassword123',
            email='regular@test.com'
        )
        # Stock item
        self.stock_item = Stock.objects.create(bloodgroup='A+', unit=15)

    # ==========================================
    # Task 4: Stock model verification
    # ==========================================
    def test_stock_model_creation(self):
        stock = Stock.objects.get(bloodgroup='A+')
        self.assertEqual(stock.bloodgroup, 'A+')
        self.assertEqual(stock.unit, 15)
        self.assertIn('A+', str(stock))

    # ==========================================
    # Task 5: Admin-only stock list table view
    # ==========================================
    def test_stock_list_view_admin_access(self):
        # Anonymous user should be redirected
        response = self.client.get(reverse('stock_list'))
        self.assertEqual(response.status_code, 302)

        # Admin login and access
        self.client.login(username='admin_test', password='testpassword123')
        response = self.client.get(reverse('stock_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Current Stock Table')
        self.assertContains(response, 'A+')
        self.assertContains(response, '15')

    def test_stock_list_view_regular_user_denied(self):
        self.client.login(username='regular_test', password='testpassword123')
        response = self.client.get(reverse('stock_list'))
        self.assertEqual(response.status_code, 302)

    # ==========================================
    # Task 6: Admin add stock entry
    # ==========================================
    def test_add_stock_view(self):
        self.client.login(username='admin_test', password='testpassword123')
        response = self.client.post(reverse('add_stock'), {
            'bloodgroup': 'B+',
            'unit': 20
        })
        self.assertEqual(response.status_code, 302)
        stock_b = Stock.objects.get(bloodgroup='B+')
        self.assertEqual(stock_b.unit, 20)

    # ==========================================
    # Task 1: Update and delete functionality
    # ==========================================
    def test_update_stock_view(self):
        self.client.login(username='admin_test', password='testpassword123')
        response = self.client.post(reverse('update_stock', args=[self.stock_item.pk]), {
            'bloodgroup': 'A+',
            'unit': 30
        })
        self.assertEqual(response.status_code, 302)
        self.stock_item.refresh_from_db()
        self.assertEqual(self.stock_item.unit, 30)

    def test_delete_stock_view(self):
        self.client.login(username='admin_test', password='testpassword123')
        response = self.client.post(reverse('delete_stock', args=[self.stock_item.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Stock.objects.filter(pk=self.stock_item.pk).exists())

    # ==========================================
    # Task 3: Patient Registration (User + Patient)
    # ==========================================
    def test_patient_registration(self):
        payload = {
            # User fields
            'first_name': 'John',
            'last_name': 'Doe',
            'username': 'johndoe',
            'email': 'johndoe@example.com',
            'password': 'SecurePassword123!',
            # Patient fields
            'age': 28,
            'bloodgroup': 'O+',
            'disease': 'Severe Anemia',
            'doctorname': 'Dr. Sarah Smith',
            'mobile': '9876543210',
            'address': '123 Main Hospital Road, City',
        }
        response = self.client.post(reverse('patient_register'), payload)
        self.assertEqual(response.status_code, 302)

        # Verify User created
        user = User.objects.get(username='johndoe')
        self.assertEqual(user.first_name, 'John')
        self.assertTrue(user.check_password('SecurePassword123!'))

        # Verify Patient created & linked
        patient = Patient.objects.get(user=user)
        self.assertEqual(patient.bloodgroup, 'O+')
        self.assertEqual(patient.age, 28)
        self.assertEqual(patient.disease, 'Severe Anemia')
        self.assertEqual(patient.doctorname, 'Dr. Sarah Smith')
        self.assertEqual(patient.get_name, 'John Doe')
        self.assertTrue(user.groups.filter(name='PATIENT').exists())

    def test_patient_registration_validation_duplicate_username(self):
        # Create an existing user
        User.objects.create_user(username='existinguser', password='password123', email='exist@example.com')
        payload = {
            'first_name': 'Jane',
            'last_name': 'Doe',
            'username': 'existinguser',
            'email': 'jane@example.com',
            'password': 'Password123!',
            'age': 30,
            'bloodgroup': 'A+',
            'disease': 'Surgery',
            'doctorname': 'Dr. Adams',
            'mobile': '9876543211',
            'address': 'Street 1, City',
        }
        response = self.client.post(reverse('patient_register'), payload)
        self.assertEqual(response.status_code, 200) # Form re-renders with error
        self.assertContains(response, 'This username is already taken')
        self.assertEqual(Patient.objects.filter(user__username='existinguser').count(), 0)

    def test_patient_registration_validation_invalid_mobile(self):
        payload = {
            'first_name': 'Alice',
            'last_name': 'Wonder',
            'username': 'alicew',
            'email': 'alice@example.com',
            'password': 'Password123!',
            'age': 25,
            'bloodgroup': 'B+',
            'disease': 'Checkup',
            'doctorname': 'Dr. Brown',
            'mobile': '12345', # Invalid mobile length
            'address': 'Wonderland',
        }
        response = self.client.post(reverse('patient_register'), payload)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please enter a valid mobile number')
        self.assertFalse(User.objects.filter(username='alicew').exists())

    def test_patient_registration_validation_invalid_age(self):
        payload = {
            'first_name': 'Bob',
            'last_name': 'Builder',
            'username': 'bobbuild',
            'email': 'bob@example.com',
            'password': 'Password123!',
            'age': 150, # Invalid age > 120
            'bloodgroup': 'AB+',
            'disease': 'Fracture',
            'doctorname': 'Dr. Stone',
            'mobile': '9876543212',
            'address': 'Brick Street',
        }
        response = self.client.post(reverse('patient_register'), payload)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please enter a valid age between 1 and 120')
        self.assertFalse(User.objects.filter(username='bobbuild').exists())

    # ==========================================
    # Task: Patient Login & Logout Views (Django Auth)
    # ==========================================
    def test_patient_login_success(self):
        # Create a registered patient user
        user = User.objects.create_user(username='patientuser', password='password123')
        Patient.objects.create(
            user=user, age=30, bloodgroup='O+', disease='None',
            doctorname='Dr. Smith', mobile='9876543210', address='City'
        )
        response = self.client.post(reverse('patient_login'), {
            'username': 'patientuser',
            'password': 'password123'
        })
        # Should redirect to patient dashboard
        self.assertRedirects(response, reverse('patient_dashboard'))
        self.assertTrue('_auth_user_id' in self.client.session)

    def test_patient_login_invalid_credentials(self):
        response = self.client.post(reverse('patient_login'), {
            'username': 'wronguser',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid username or password')
        self.assertFalse('_auth_user_id' in self.client.session)

    def test_patient_logout(self):
        user = User.objects.create_user(username='patientlogout', password='password123')
        self.client.login(username='patientlogout', password='password123')
        response = self.client.get(reverse('patient_logout'))
        # Should redirect to patient login
        self.assertRedirects(response, reverse('patient_login'))
        self.assertFalse('_auth_user_id' in self.client.session)

    def test_patient_dashboard_requires_login(self):
        response = self.client.get(reverse('patient_dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('patient_login'), response.url)

    def test_patient_dashboard_non_patient_access_denied(self):
        # Regular user without a patient profile
        regular_user = User.objects.create_user(username='regularperson', password='password123')
        self.client.force_login(regular_user)
        response = self.client.get(reverse('patient_dashboard'), follow=True)
        self.assertRedirects(response, reverse('home'))
        self.assertContains(response, 'Access denied. The patient dashboard is only accessible to registered patients.')

    def test_patient_dashboard_admin_access_redirected(self):
        # Admin user without a patient profile is redirected to stock inventory
        self.client.force_login(self.admin)
        response = self.client.get(reverse('patient_dashboard'), follow=True)
        self.assertRedirects(response, reverse('stock_list'))
        self.assertContains(response, 'Access denied. The patient dashboard is only accessible to registered patients.')


    def test_patient_dashboard_content_and_session(self):
        # Create user and patient profile
        user = User.objects.create_user(username='dashuser', password='password123', first_name='Alex')
        patient = Patient.objects.create(
            user=user, age=35, bloodgroup='A+', disease='Thalassemia',
            doctorname='Dr. Johnson', mobile='9876543299', address='45 Health Ave'
        )
        # Login
        login_resp = self.client.post(reverse('patient_login'), {
            'username': 'dashuser',
            'password': 'password123'
        })
        self.assertRedirects(login_resp, reverse('patient_dashboard'))

        # Verify session state
        self.assertEqual(self.client.session.get('role'), 'patient')
        self.assertEqual(self.client.session.get('patient_id'), patient.id)
        self.assertEqual(self.client.session.get('bloodgroup'), 'A+')

        # Access dashboard
        response = self.client.get(reverse('patient_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Welcome, Alex!')
        self.assertContains(response, 'Session Active (Patient)')
        self.assertContains(response, 'A+')
        self.assertContains(response, 'Thalassemia')
        self.assertContains(response, 'Dr. Johnson')
        self.assertContains(response, 'Compatible Donor Groups')

    # ==========================================
    # Task 2: UI responsiveness and Home page
    # ==========================================
    def test_home_page_rendered_with_bootstrap(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Blood Bank Management System')
        self.assertContains(response, 'Current Blood Stock')
        self.assertContains(response, 'cdn.jsdelivr.net/npm/bootstrap@5.3.3')

    # ==========================================
    # Task: Donor Registration View with Validation & DB Save
    # ==========================================
    def test_donor_register_get_renders_form(self):
        response = self.client.get(reverse('donor_register'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Blood Donor Registration Form')
        self.assertContains(response, 'Donor Profile Details')
        self.assertContains(response, 'csrfmiddlewaretoken')

    def test_donor_registration_success(self):
        payload = {
            'first_name': 'David',
            'last_name': 'Donor',
            'username': 'daviddonor',
            'email': 'david.donor@example.com',
            'password': 'SecureDonor123!',
            'bloodgroup': 'O+',
            'address': '742 Evergreen Terrace',
            'mobile': '9876543210',
        }
        response = self.client.post(reverse('donor_register'), payload)
        self.assertRedirects(response, reverse('donor_login'))

        # Check User created and password safely hashed
        user = User.objects.get(username='daviddonor')
        self.assertEqual(user.first_name, 'David')
        self.assertEqual(user.email, 'david.donor@example.com')
        self.assertTrue(user.check_password('SecureDonor123!'))

        # Check DONOR group assigned
        self.assertTrue(user.groups.filter(name='DONOR').exists())

        # Check Donor profile created and linked
        donor = Donor.objects.get(user=user)
        self.assertEqual(donor.bloodgroup, 'O+')
        self.assertEqual(donor.mobile, '9876543210')
        self.assertEqual(donor.address, '742 Evergreen Terrace')
        self.assertEqual(donor.get_name, 'David Donor')

    def test_donor_registration_validation_duplicate_username(self):
        # Create user with same username
        User.objects.create_user(username='existingdonor', email='old@example.com', password='Password123!')

        payload = {
            'first_name': 'New',
            'last_name': 'Donor',
            'username': 'existingdonor',
            'email': 'new@example.com',
            'password': 'Password123!',
            'bloodgroup': 'A+',
            'address': '123 Main St',
            'mobile': '9876543210',
        }
        response = self.client.post(reverse('donor_register'), payload)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This username is already taken')
        self.assertEqual(Donor.objects.filter(user__username='existingdonor').count(), 0)

    def test_donor_registration_validation_invalid_mobile(self):
        payload = {
            'first_name': 'Frank',
            'last_name': 'Donor',
            'username': 'frankdonor',
            'email': 'frank@example.com',
            'password': 'Password123!',
            'bloodgroup': 'B+',
            'address': '456 Oak Ave',
            'mobile': '12345', # Less than 10 digits
        }
        response = self.client.post(reverse('donor_register'), payload)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please enter a valid mobile number')
        self.assertFalse(User.objects.filter(username='frankdonor').exists())

    def test_donor_registration_validation_short_password(self):
        payload = {
            'first_name': 'Grace',
            'last_name': 'Donor',
            'username': 'gracedonor',
            'email': 'grace@example.com',
            'password': '123', # Less than 6 characters
            'bloodgroup': 'AB-',
            'address': '789 Pine St',
            'mobile': '9876543210',
        }
        response = self.client.post(reverse('donor_register'), payload)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Password must be at least 6 characters long')
        self.assertFalse(User.objects.filter(username='gracedonor').exists())

    # ==========================================
    # Task: Donor Registration Forms (User & Donor)
    # ==========================================
    def test_donor_user_form_valid(self):
        form_data = {
            'first_name': 'Henry',
            'last_name': 'Ford',
            'username': 'henryford',
            'email': 'henry@example.com',
            'password': 'Password123!',
        }
        form = DonorUserForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_donor_form_valid(self):
        form_data = {
            'bloodgroup': 'O-',
            'address': '100 Sunset Blvd',
            'mobile': '9876543210',
        }
        form = DonorForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_donor_form_invalid_mobile(self):
        form_data = {
            'bloodgroup': 'O-',
            'address': '100 Sunset Blvd',
            'mobile': 'invalid123',
        }
        form = DonorForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('mobile', form.errors)

    # ==========================================
    # Tasks 1, 2, 3: Donor Authentication & Dashboard Access Control
    # ==========================================
    def test_donor_login_success(self):
        user = User.objects.create_user(username='logindonor', password='Password123!', first_name='Leo')
        donor = Donor.objects.create(user=user, bloodgroup='B+', address='88 River Road', mobile='9876543210')

        response = self.client.post(reverse('donor_login'), {
            'username': 'logindonor',
            'password': 'Password123!',
        })
        self.assertRedirects(response, reverse('donor_dashboard'))
        self.assertEqual(self.client.session.get('role'), 'donor')
        self.assertEqual(self.client.session.get('donor_id'), donor.id)
        self.assertEqual(self.client.session.get('bloodgroup'), 'B+')

    def test_donor_login_invalid_credentials(self):
        response = self.client.post(reverse('donor_login'), {
            'username': 'nonexistent',
            'password': 'wrongpassword',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid username or password')

    def test_donor_logout(self):
        user = User.objects.create_user(username='logoutdonor', password='Password123!')
        Donor.objects.create(user=user, bloodgroup='A-', address='10 Street', mobile='9876543210')
        self.client.force_login(user)

        response = self.client.get(reverse('donor_logout'))
        self.assertRedirects(response, reverse('donor_login'))
        self.assertFalse('_auth_user_id' in self.client.session)

    def test_donor_dashboard_requires_login(self):
        # Task 3: Unauthenticated user restricted from donor dashboard
        response = self.client.get(reverse('donor_dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('donor_login'), response.url)

    def test_donor_dashboard_non_donor_access_denied(self):
        # Task 3: Authenticated non-donor user restricted from donor dashboard
        non_donor = User.objects.create_user(username='nondonoruser', password='Password123!')
        self.client.force_login(non_donor)

        response = self.client.get(reverse('donor_dashboard'), follow=True)
        self.assertRedirects(response, reverse('home'))
        self.assertContains(response, 'Access denied. The donor dashboard is only accessible to registered donors.')

    def test_donor_dashboard_admin_access_redirected(self):
        # Task 3: Staff/admin accessing donor dashboard redirected to stock list
        self.client.force_login(self.admin)
        response = self.client.get(reverse('donor_dashboard'), follow=True)
        self.assertRedirects(response, reverse('stock_list'))
        self.assertContains(response, 'Access denied. The donor dashboard is only accessible to registered donors.')

    def test_donor_dashboard_content_and_session(self):
        # Task 2: Authenticated donor accesses personalized dashboard
        user = User.objects.create_user(username='activedonor', password='Password123!', first_name='Emma')
        donor = Donor.objects.create(user=user, bloodgroup='O-', address='500 Hope St', mobile='9876543210')

        self.client.force_login(user)
        # Populate session state
        session = self.client.session
        session['role'] = 'donor'
        session['donor_id'] = donor.id
        session['bloodgroup'] = 'O-'
        session.save()

        response = self.client.get(reverse('donor_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Welcome, Emma!')
        self.assertContains(response, 'Session Active (Donor)')
        self.assertContains(response, 'O-')
        self.assertContains(response, 'Universal Red Cell Donor')
        self.assertContains(response, '500 Hope St')
        self.assertContains(response, '9876543210')

    # ==========================================
    # Tasks 1, 2 & 3: Patient Email OTP Authentication
    # ==========================================
    def test_patient_email_otp_form_validation(self):
        # Task 1: Create a form where patients can enter their registered email to receive OTP
        user = User.objects.create_user(username='otpuser1', email='otpuser1@example.com', password='Password123!')
        Patient.objects.create(
            user=user, age=30, bloodgroup='B+', disease='None',
            doctorname='Dr. Smith', mobile='9876543210', address='123 Road'
        )

        # Valid registered patient email
        form = PatientEmailOTPForm(data={'email': 'otpuser1@example.com'})
        self.assertTrue(form.is_valid())

        # Non-existent email
        invalid_form = PatientEmailOTPForm(data={'email': 'notfound@example.com'})
        self.assertFalse(invalid_form.is_valid())
        self.assertIn('email', invalid_form.errors)

        # Non-patient user email
        User.objects.create_user(username='regularonly', email='regular@example.com', password='Password123!')
        non_patient_form = PatientEmailOTPForm(data={'email': 'regular@example.com'})
        self.assertFalse(non_patient_form.is_valid())
        self.assertIn('email', non_patient_form.errors)

    def test_otp_verification_form_validation(self):
        # Task 3: Verification form validation
        valid_form = OTPVerificationForm(data={'otp': '654321'})
        self.assertTrue(valid_form.is_valid())

        invalid_form_letters = OTPVerificationForm(data={'otp': 'abc123'})
        self.assertFalse(invalid_form_letters.is_valid())

        invalid_form_length = OTPVerificationForm(data={'otp': '1234'})
        self.assertFalse(invalid_form_length.is_valid())

    def test_patient_request_otp_get(self):
        # Task 1: Form page renders successfully
        response = self.client.get(reverse('patient_request_otp'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Patient OTP Verification')
        self.assertContains(response, 'Send Verification OTP')

    def test_patient_request_otp_generates_random_otp_and_sends_email(self):
        # Task 2: Generate random OTP and send it to the patient's email using Django's email backend
        mail.outbox.clear()
        user = User.objects.create_user(username='patientmail', email='patientmail@example.com', password='Password123!')
        Patient.objects.create(
            user=user, age=40, bloodgroup='O+', disease='Routine',
            doctorname='Dr. Grey', mobile='9876543210', address='Grey Clinic'
        )

        response = self.client.post(reverse('patient_request_otp'), {
            'email': 'patientmail@example.com'
        })
        self.assertRedirects(response, reverse('patient_verify_otp'))

        # Verify email was dispatched via Django email backend
        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]
        self.assertIn('patientmail@example.com', sent_email.to)
        self.assertIn('Verification OTP', sent_email.subject)

        # Verify 6-digit random OTP generated in session and included in email body
        session_otp = self.client.session.get('patient_otp')
        self.assertIsNotNone(session_otp)
        self.assertEqual(len(session_otp), 6)
        self.assertTrue(session_otp.isdigit())
        self.assertIn(session_otp, sent_email.body)

    def test_patient_verify_otp_get_without_session_redirects(self):
        # Task 3: Direct access without requesting OTP redirects back
        response = self.client.get(reverse('patient_verify_otp'))
        self.assertRedirects(response, reverse('patient_request_otp'))

    def test_patient_verify_otp_invalid_code(self):
        # Task 3: Entering incorrect OTP is rejected
        user = User.objects.create_user(username='otpwrong', email='wrong@example.com', password='Password123!')
        Patient.objects.create(
            user=user, age=22, bloodgroup='A+', disease='Checkup',
            doctorname='Dr. House', mobile='9876543210', address='1 Clinic St'
        )
        session = self.client.session
        session['patient_otp'] = '999888'
        session['otp_user_id'] = user.id
        session['otp_email'] = 'wrong@example.com'
        import time
        session['otp_timestamp'] = time.time()
        session.save()

        response = self.client.post(reverse('patient_verify_otp'), {
            'otp': '111222' # Incorrect code
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid OTP code')
        self.assertFalse('_auth_user_id' in self.client.session)

    def test_patient_verify_otp_success_logs_in_patient(self):
        # Task 3: Entering correct OTP logs patient in and navigates to dashboard
        user = User.objects.create_user(username='otpsuccess', email='success@example.com', password='Password123!', first_name='Clara')
        patient = Patient.objects.create(
            user=user, age=29, bloodgroup='AB-', disease='None',
            doctorname='Dr. Watson', mobile='9876543210', address='221B Baker St'
        )
        session = self.client.session
        session['patient_otp'] = '456789'
        session['otp_user_id'] = user.id
        session['otp_email'] = 'success@example.com'
        import time
        session['otp_timestamp'] = time.time()
        session.save()

        response = self.client.post(reverse('patient_verify_otp'), {
            'otp': '456789'
        })
        self.assertRedirects(response, reverse('patient_dashboard'))

        # Verify patient authenticated in session
        self.assertEqual(int(self.client.session.get('_auth_user_id')), user.id)
        self.assertEqual(self.client.session.get('role'), 'patient')
        self.assertEqual(self.client.session.get('patient_id'), patient.id)
        # Verify OTP session keys cleared
        self.assertNotIn('patient_otp', self.client.session)

    def test_patient_verify_otp_expired_code(self):
        # Task 3: Expired OTP is rejected
        user = User.objects.create_user(username='otpexpired', email='expired@example.com', password='Password123!')
        Patient.objects.create(
            user=user, age=29, bloodgroup='AB-', disease='None',
            doctorname='Dr. Watson', mobile='9876543210', address='221B Baker St'
        )
        session = self.client.session
        session['patient_otp'] = '123456'
        session['otp_user_id'] = user.id
        session['otp_email'] = 'expired@example.com'
        import time
        session['otp_timestamp'] = time.time() - 700 # Expired (>600 seconds)
        session.save()

        response = self.client.post(reverse('patient_verify_otp'), {
            'otp': '123456'
        })
        self.assertRedirects(response, reverse('patient_request_otp'))




