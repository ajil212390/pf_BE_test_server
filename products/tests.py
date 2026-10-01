from decimal import Decimal
from types import SimpleNamespace
from django.test import SimpleTestCase
from django.contrib.auth.hashers import check_password, make_password
from rest_framework.test import APIClient
from rest_framework.test import APIRequestFactory
from rest_framework.exceptions import AuthenticationFailed
from unittest.mock import patch
from .views.admin_views import _build_financial_summary, _rollup_account_rows
from .views.supplier_views import _is_note_entry
from .views.supplier_product_views import _get_product_taxonomy
from .views.supplier_views import _commitment_coin_cost
from .password_utils import hash_password, verify_and_upgrade_password
from .api_auth import RoleTokenAuthentication, issue_access_token


class FinancialSummaryTests(SimpleTestCase):
    def test_build_financial_summary_formats_values(self):
        summary = _build_financial_summary(
            total_count=3,
            bill_count=4,
            bill_amount=Decimal('1250.50'),
            note_count=2,
            note_amount=Decimal('500.25'),
            paid_amount=Decimal('1000.00'),
            balance_amount=Decimal('250.50'),
        )

        self.assertEqual(summary['count'], 3)
        self.assertEqual(summary['bills_count'], 4)
        self.assertEqual(summary['bills_amount'], 1250.5)
        self.assertEqual(summary['notes_count'], 2)
        self.assertEqual(summary['notes_amount'], 500.25)
        self.assertEqual(summary['paid_amount'], 1000.0)
        self.assertEqual(summary['balance_amount'], 250.5)

    def test_rollup_account_rows_sums_each_account_balance(self):
        rows = [
            {
                'bills_count': 2,
                'bills_amount': 1450.0,
                'credit_notes_count': 1,
                'credit_notes_amount': 200.0,
                'paid_amount': 1000.0,
                'balance_amount': 1250.0,
            },
            {
                'bills_count': 2,
                'bills_amount': 2800.0,
                'credit_notes_count': 1,
                'credit_notes_amount': 300.0,
                'paid_amount': 1500.0,
                'balance_amount': 2000.0,
            },
        ]

        summary = _rollup_account_rows(rows)

        self.assertEqual(summary['bills_count'], 4)
        self.assertEqual(summary['bills_amount'], 4250.0)
        self.assertEqual(summary['notes_count'], 2)
        self.assertEqual(summary['notes_amount'], 500.0)
        self.assertEqual(summary['paid_amount'], 2500.0)
        self.assertEqual(summary['balance_amount'], 3250.0)

    def test_return_type_is_treated_as_note(self):
        self.assertTrue(_is_note_entry('Return'))
        self.assertTrue(_is_note_entry('Sales Return'))
        self.assertTrue(_is_note_entry('Credit Note'))
        self.assertFalse(_is_note_entry('Sales'))
        self.assertFalse(_is_note_entry('Purchase'))

    def test_supplier_product_taxonomy_uses_model_field_names(self):
        product = SimpleNamespace(
            productcategoryid=SimpleNamespace(productcategoryname='Bakery'),
            productunitid=SimpleNamespace(productunitname='Packet'),
        )

        self.assertEqual(_get_product_taxonomy(product), ('Bakery', 'Packet'))

    def test_coin_recharge_routes_require_payment_integration(self):
        client = APIClient()
        paths = [
            ('/api/enduser/wallet/1/recharge/', 'enduser', 1, {}),
            ('/api/company/wallet/1/recharge/', 'company', 10, {'company_id': 1}),
            ('/api/supplier/wallet/1/recharge/', 'supplier', 1, {'supplier_user_id': 1}),
        ]

        for path, role, user_id, identity in paths:
            token = issue_access_token(role, user_id, **identity)
            client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
            response = client.post(path, {'amount': 100000}, format='json')
            self.assertEqual(response.status_code, 503)
            self.assertFalse(response.data['success'])

        supplier_token = issue_access_token('supplier', 1, supplier_user_id=1)
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {supplier_token}')
        self.assertEqual(client.get('/api/supplier/wallet/1/').status_code, 503)
        self.assertEqual(
            client.post('/api/supplier/wallet/1/deduct/', {'amount': 25}, format='json').status_code,
            503,
        )

    def test_sensitive_wallet_order_and_commitment_routes_require_authentication(self):
        client = APIClient()
        self.assertEqual(client.get('/api/enduser/wallet/1/').status_code, 401)
        self.assertEqual(client.get('/api/company/wallet/1/').status_code, 401)
        self.assertEqual(
            client.post('/api/company/wallet/1/deduct/', {'amount': 1}, format='json').status_code,
            401,
        )
        self.assertEqual(
            client.post('/api/chat/messages/1/confirm-bill/', {}, format='json').status_code,
            401,
        )
        self.assertEqual(
            client.post('/api/chat/company-buyer-profile/', {'company_id': 1}, format='json').status_code,
            401,
        )
        self.assertEqual(
            client.get('/api/commitments/?bill_no=TEST').status_code,
            401,
        )

    def test_signed_role_token_round_trip_and_invalid_token_rejection(self):
        token = issue_access_token('company', 12, company_id=5)
        request = APIRequestFactory().get('/', HTTP_AUTHORIZATION=f'Bearer {token}')
        principal, _ = RoleTokenAuthentication().authenticate(request)
        self.assertEqual(principal.role, 'company')
        self.assertEqual(principal.user_id, 12)
        self.assertEqual(principal.company_id, 5)

        invalid_request = APIRequestFactory().get('/', HTTP_AUTHORIZATION='Bearer invalid')
        with self.assertRaises(AuthenticationFailed):
            RoleTokenAuthentication().authenticate(invalid_request)

    @patch('products.views.auth_views.Users.objects.get')
    def test_company_login_returns_token_for_hashed_password(self, get_user):
        company = SimpleNamespace(
            companyid=5,
            companyname='Test Store',
            companyphonenumber='1234567890',
        )
        get_user.return_value = SimpleNamespace(
            userid=12,
            username='store-user',
            useremail='store@example.test',
            userpassword=make_password('test-password'),
            companyid=company,
        )

        response = APIClient().post(
            '/api/login/',
            {'username': 'store-user', 'userpassword': 'test-password'},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        request = APIRequestFactory().get('/', HTTP_AUTHORIZATION=f"Bearer {response.data['access_token']}")
        principal, _ = RoleTokenAuthentication().authenticate(request)
        self.assertEqual(principal.role, 'company')
        self.assertEqual(principal.company_id, 5)

    @patch('products.views.auth_views.EndUser.objects.get')
    def test_enduser_login_returns_token_for_hashed_password(self, get_enduser):
        get_enduser.return_value = SimpleNamespace(
            endsuerid=21,
            endusername='shopper',
            enduseremail='shopper@example.test',
            enduserphone='1234567890',
            enduserpassword=make_password('test-password'),
            coins_balance=75,
            is_verified_customer=False,
        )

        response = APIClient().post(
            '/api/login-enduser/',
            {'endusername': 'shopper', 'enduserpassword': 'test-password'},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        request = APIRequestFactory().get('/', HTTP_AUTHORIZATION=f"Bearer {response.data['access_token']}")
        principal, _ = RoleTokenAuthentication().authenticate(request)
        self.assertEqual(principal.role, 'enduser')
        self.assertEqual(principal.user_id, 21)

    def test_protected_wallet_and_buyer_profile_reject_wrong_role_or_owner(self):
        client = APIClient()
        enduser_token = issue_access_token('enduser', 1)
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {enduser_token}')
        self.assertEqual(client.get('/api/company/wallet/1/').status_code, 403)

        company_token = issue_access_token('company', 10, company_id=1)
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {company_token}')
        self.assertEqual(
            client.post('/api/chat/company-buyer-profile/', {'company_id': 2}, format='json').status_code,
            403,
        )

    def test_role_scoped_admin_catalog_and_provisioning_endpoints(self):
        client = APIClient()
        enduser_token = issue_access_token('enduser', 1)
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {enduser_token}')

        self.assertEqual(client.get('/api/admin/overview/').status_code, 403)
        self.assertEqual(client.post('/api/products/', {}, format='json').status_code, 403)
        self.assertEqual(client.post('/api/categories/', {}, format='json').status_code, 403)
        self.assertEqual(
            client.post('/api/supplier/managers/register/', {
                'supplier_user_id': 1,
                'manager_name': 'Unauthorized',
                'manager_username': 'unauthorized',
                'manager_password': 'not-used',
            }, format='json').status_code,
            403,
        )
        self.assertEqual(
            client.post('/api/supplier/executives/register/', {
                'manager_id': 1,
                'executive_name': 'Unauthorized',
                'executive_username': 'unauthorized',
                'executive_password': 'not-used',
            }, format='json').status_code,
            403,
        )
        company_token = issue_access_token('company', 10, company_id=1)
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {company_token}')
        self.assertEqual(
            client.post('/api/chat/messages/1/confirm-bill/', {}, format='json').status_code,
            403,
        )

        executive_token = issue_access_token(
            'executive',
            1,
            executive_id=1,
            manager_id=1,
            supplier_user_id=1,
        )
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {executive_token}')
        self.assertEqual(
            client.get('/api/supplier/1/products/?company_id=1&executive_id=2').status_code,
            403,
        )

    def test_company_chat_and_order_lists_reject_other_company_ids(self):
        client = APIClient()
        token = issue_access_token('company', 10, company_id=1)
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(client.get('/api/chat/conversations/company/2/').status_code, 403)
        self.assertEqual(client.get('/api/chat/orders/company/2/').status_code, 403)

    def test_password_hashing_and_legacy_upgrade(self):
        hashed = hash_password('new-password')
        self.assertNotEqual(hashed, 'new-password')
        self.assertTrue(check_password('new-password', hashed))

        saved_fields = []
        user = SimpleNamespace(
            password='legacy-password',
            save=lambda **kwargs: saved_fields.append(kwargs.get('update_fields')),
        )
        self.assertTrue(verify_and_upgrade_password(user, 'password', 'legacy-password'))
        self.assertTrue(check_password('legacy-password', user.password))
        self.assertEqual(saved_fields, [['password']])

        self.assertFalse(verify_and_upgrade_password(user, 'password', 'wrong-password'))

    def test_commitment_coin_cost_matches_extension_schedule(self):
        self.assertEqual(_commitment_coin_cost(5, 0), 50)
        self.assertEqual(_commitment_coin_cost(5, 1), 100)
        self.assertEqual(_commitment_coin_cost(5, 5), 600)
        self.assertEqual(_commitment_coin_cost(365, 10), 1000)
        self.assertEqual(_commitment_coin_cost(0, 0), 0)
