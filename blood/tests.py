from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from blood.models import Stock, Patient


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
    # Task 2: UI responsiveness and Home page
    # ==========================================
    def test_home_page_rendered_with_bootstrap(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Blood Bank Management System')
        self.assertContains(response, 'Current Blood Stock')
        self.assertContains(response, 'cdn.jsdelivr.net/npm/bootstrap@5.3.3')
