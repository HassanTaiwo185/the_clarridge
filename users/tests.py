from django.test import TestCase, override_settings
from django.core.cache import cache
from rest_framework_simplejwt.tokens import RefreshToken


from users.otp import (
    generate_otp,
    stash_pending_registration,
    get_pending_registration,
    clear_pending_registration,
    stash_password_reset_otp,
    get_password_reset_otp,
    clear_password_reset_otp,
)

TEST_CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
}


@override_settings(CACHES=TEST_CACHES)
class GenerateOtpTests(TestCase):
    def test_returns_six_digit_string(self):
        otp = generate_otp("a@example.com")
        self.assertIsInstance(otp, str)
        self.assertEqual(len(otp), 6)
        self.assertTrue(otp.isdigit())

    def test_within_valid_numeric_range(self):
        for _ in range(50):
            otp = generate_otp("a@example.com")
            self.assertTrue(100000 <= int(otp) <= 999999)


@override_settings(CACHES=TEST_CACHES)
class PendingRegistrationTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_stash_and_retrieve_roundtrip(self):
        stash_pending_registration("a@example.com", "123456", {"first_name": "A"})
        pending = get_pending_registration("a@example.com")
        self.assertEqual(pending["otp"], "123456")
        self.assertEqual(pending["data"]["first_name"], "A")

    def test_get_returns_none_when_missing(self):
        self.assertIsNone(get_pending_registration("nobody@example.com"))

    def test_clear_removes_key(self):
        stash_pending_registration("a@example.com", "123456", {})
        clear_pending_registration("a@example.com")
        self.assertIsNone(get_pending_registration("a@example.com"))

    def test_clear_on_nonexistent_key_does_not_error(self):
        clear_pending_registration("ghost@example.com")  # should not raise

    def test_separate_emails_do_not_collide(self):
        stash_pending_registration("a@example.com", "111111", {"n": "A"})
        stash_pending_registration("b@example.com", "222222", {"n": "B"})
        self.assertEqual(get_pending_registration("a@example.com")["otp"], "111111")
        self.assertEqual(get_pending_registration("b@example.com")["otp"], "222222")

    def test_restashing_same_email_overwrites(self):
        stash_pending_registration("a@example.com", "111111", {"n": "old"})
        stash_pending_registration("a@example.com", "222222", {"n": "new"})
        pending = get_pending_registration("a@example.com")
        self.assertEqual(pending["otp"], "222222")
        self.assertEqual(pending["data"]["n"], "new")


@override_settings(CACHES=TEST_CACHES)
class PasswordResetOtpTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_stash_and_retrieve(self):
        stash_password_reset_otp("a@example.com", "654321")
        self.assertEqual(get_password_reset_otp("a@example.com"), "654321")

    def test_get_returns_none_when_missing(self):
        self.assertIsNone(get_password_reset_otp("nobody@example.com"))

    def test_clear_removes_key(self):
        stash_password_reset_otp("a@example.com", "654321")
        clear_password_reset_otp("a@example.com")
        self.assertIsNone(get_password_reset_otp("a@example.com"))

    def test_reset_namespace_isolated_from_registration_namespace(self):
        stash_pending_registration("a@example.com", "111111", {})
        stash_password_reset_otp("a@example.com", "999999")
        self.assertEqual(get_pending_registration("a@example.com")["otp"], "111111")
        self.assertEqual(get_password_reset_otp("a@example.com"), "999999")

# ---------------------------------------------------------
# Registration & email verification (API-level tests)
# ---------------------------------------------------------

from django.urls import reverse
from django.core import mail
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth.models import User

from users.models import Profile


VALID_REGISTER_PAYLOAD = {
    "first_name": "Jane",
    "last_name": "Doe",
    "email": "jane@example.com",
    "password": "StrongPass123!",
    "confirm_password": "StrongPass123!",
    "phone_number": "+2348012345678",
    "date_of_birth": "1995-04-12",
}


@override_settings(CACHES=TEST_CACHES, EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class RegisterViewTests(APITestCase):
    def setUp(self):
        cache.clear()
        mail.outbox = []
        self.url = reverse('register')

    # ---------- positive ----------

    def test_valid_registration_returns_201(self):
        response = self.client.post(self.url, VALID_REGISTER_PAYLOAD, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_valid_registration_does_not_create_user_yet(self):
        # core design requirement: no DB row until OTP verified
        self.client.post(self.url, VALID_REGISTER_PAYLOAD, format='json')
        self.assertFalse(User.objects.filter(email="jane@example.com").exists())

    def test_valid_registration_sends_one_email(self):
        self.client.post(self.url, VALID_REGISTER_PAYLOAD, format='json')
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("jane@example.com", mail.outbox[0].to)

    def test_valid_registration_stashes_pending_record(self):
        from users.otp import get_pending_registration
        self.client.post(self.url, VALID_REGISTER_PAYLOAD, format='json')
        pending = get_pending_registration("jane@example.com")
        self.assertIsNotNone(pending)
        self.assertEqual(pending["data"]["first_name"], "Jane")

    # ---------- negative ----------

    def test_password_mismatch_returns_400(self):
        payload = {**VALID_REGISTER_PAYLOAD, "confirm_password": "Different123!"}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("confirm_password", response.data)

    def test_password_mismatch_sends_no_email(self):
        payload = {**VALID_REGISTER_PAYLOAD, "confirm_password": "Different123!"}
        self.client.post(self.url, payload, format='json')
        self.assertEqual(len(mail.outbox), 0)

    def test_duplicate_email_returns_400(self):
        User.objects.create_user(username="jane@example.com", email="jane@example.com", password="x")
        response = self.client.post(self.url, VALID_REGISTER_PAYLOAD, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_invalid_email_format_returns_400(self):
        payload = {**VALID_REGISTER_PAYLOAD, "email": "not-an-email"}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_required_field_returns_400(self):
        payload = {**VALID_REGISTER_PAYLOAD}
        del payload["phone_number"]
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("phone_number", response.data)

    def test_invalid_date_of_birth_format_returns_400(self):
        payload = {**VALID_REGISTER_PAYLOAD, "date_of_birth": "not-a-date"}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ---------- boundary / edge ----------

    def test_empty_payload_returns_400_with_all_fields_flagged(self):
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        for field in ["first_name", "last_name", "email", "password", "phone_number", "date_of_birth"]:
            self.assertIn(field, response.data)

    def test_reregistering_same_email_before_verification_overwrites_pending(self):
        # edge case: user submits registration twice before verifying — should just refresh OTP, not error
        self.client.post(self.url, VALID_REGISTER_PAYLOAD, format='json')
        first_otp = mail.outbox[0].body
        response = self.client.post(self.url, VALID_REGISTER_PAYLOAD, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(mail.outbox), 2)


@override_settings(CACHES=TEST_CACHES, EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class VerifyEmailViewTests(APITestCase):
    def setUp(self):
        cache.clear()
        mail.outbox = []
        self.register_url = reverse('register')
        self.verify_url = reverse('verify-email')

    def _register_and_get_otp(self, payload=None):
        payload = payload or VALID_REGISTER_PAYLOAD
        self.client.post(self.register_url, payload, format='json')
        from users.otp import get_pending_registration
        pending = get_pending_registration(payload["email"])
        return pending["otp"]

    # ---------- positive ----------

    def test_correct_otp_creates_user(self):
        otp = self._register_and_get_otp()
        response = self.client.post(self.verify_url, {"email": "jane@example.com", "otp": otp}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(User.objects.filter(email="jane@example.com").exists())

    def test_verified_user_is_inactive_pending_admin_approval(self):
        otp = self._register_and_get_otp()
        self.client.post(self.verify_url, {"email": "jane@example.com", "otp": otp}, format='json')
        user = User.objects.get(email="jane@example.com")
        self.assertFalse(user.is_active)

    def test_verified_user_has_profile_created(self):
        otp = self._register_and_get_otp()
        self.client.post(self.verify_url, {"email": "jane@example.com", "otp": otp}, format='json')
        user = User.objects.get(email="jane@example.com")
        self.assertTrue(Profile.objects.filter(user=user).exists())
        self.assertEqual(user.profile.phone_number, "+2348012345678")

    def test_successful_verification_clears_pending_record(self):
        from users.otp import get_pending_registration
        otp = self._register_and_get_otp()
        self.client.post(self.verify_url, {"email": "jane@example.com", "otp": otp}, format='json')
        self.assertIsNone(get_pending_registration("jane@example.com"))

    def test_password_is_hashed_not_plaintext(self):
        otp = self._register_and_get_otp()
        self.client.post(self.verify_url, {"email": "jane@example.com", "otp": otp}, format='json')
        user = User.objects.get(email="jane@example.com")
        self.assertNotEqual(user.password, "StrongPass123!")
        self.assertTrue(user.check_password("StrongPass123!"))

    # ---------- negative ----------

    def test_wrong_otp_returns_400(self):
        self._register_and_get_otp()
        response = self.client.post(self.verify_url, {"email": "jane@example.com", "otp": "000000"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(email="jane@example.com").exists())

    def test_verify_without_prior_registration_returns_400(self):
        response = self.client.post(self.verify_url, {"email": "ghost@example.com", "otp": "123456"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_otp_wrong_length_returns_400(self):
        self._register_and_get_otp()
        response = self.client.post(self.verify_url, {"email": "jane@example.com", "otp": "123"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verifying_twice_second_attempt_fails(self):
        # edge case: OTP cleared after first success, replay should fail
        otp = self._register_and_get_otp()
        self.client.post(self.verify_url, {"email": "jane@example.com", "otp": otp}, format='json')
        response = self.client.post(self.verify_url, {"email": "jane@example.com", "otp": otp}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ---------- boundary ----------

    def test_otp_expiry_boundary(self):
        from users.otp import OTP_TTL_SECONDS
        import time
        otp = self._register_and_get_otp()
        # simulate TTL passing by manually deleting the cache key (locmem has no time-travel helper)
        cache.delete(f"pending_registration:jane@example.com")
        response = self.client.post(self.verify_url, {"email": "jane@example.com", "otp": otp}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------
# Change password (authenticated user changes their own password)
# ---------------------------------------------------------




def get_auth_headers(user):
    """Helper: build the Authorization header for a JWT-authenticated request."""
    token = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {token.access_token}"}


@override_settings(CACHES=TEST_CACHES)
class ChangePasswordViewTests(APITestCase):
    def setUp(self):
        self.url = reverse('change-password')
        self.user = User.objects.create_user(
            username="jane@example.com",
            email="jane@example.com",
            password="OldPass123!",
            is_active=True,
        )
        Profile.objects.create(
            user=self.user,
            phone_number="+2348012345678",
            date_of_birth="1995-04-12",
        )
        self.headers = get_auth_headers(self.user)

    # ---------- positive ----------

    def test_correct_current_password_changes_it(self):
        payload = {
            "current_password": "OldPass123!",
            "new_password": "NewPass456!",
            "confirm_password": "NewPass456!",
        }
        response = self.client.post(self.url, payload, format='json', **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewPass456!"))
        self.assertFalse(self.user.check_password("OldPass123!"))

    def test_new_password_is_hashed(self):
        payload = {
            "current_password": "OldPass123!",
            "new_password": "NewPass456!",
            "confirm_password": "NewPass456!",
        }
        self.client.post(self.url, payload, format='json', **self.headers)
        self.user.refresh_from_db()
        self.assertNotEqual(self.user.password, "NewPass456!")

    # ---------- negative ----------

    def test_wrong_current_password_returns_400(self):
        payload = {
            "current_password": "WrongPass!",
            "new_password": "NewPass456!",
            "confirm_password": "NewPass456!",
        }
        response = self.client.post(self.url, payload, format='json', **self.headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("current_password", response.data)

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("OldPass123!"))  # unchanged

    def test_new_password_mismatch_returns_400(self):
        payload = {
            "current_password": "OldPass123!",
            "new_password": "NewPass456!",
            "confirm_password": "Different789!",
        }
        response = self.client.post(self.url, payload, format='json', **self.headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("confirm_password", response.data)

    def test_unauthenticated_request_returns_401(self):
        payload = {
            "current_password": "OldPass123!",
            "new_password": "NewPass456!",
            "confirm_password": "NewPass456!",
        }
        response = self.client.post(self.url, payload, format='json')  # no auth header
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_missing_fields_returns_400(self):
        response = self.client.post(self.url, {}, format='json', **self.headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ---------- boundary / edge ----------

    def test_cannot_change_another_users_password_via_body(self):
        # edge case: even if someone tries to smuggle a different email/user_id
        # into the payload, ChangePasswordSerializer must ignore it and only
        # ever act on request.user — there is no field in the payload for this,
        # so this test just confirms extra/unexpected fields don't break anything.
        other_user = User.objects.create_user(
            username="bob@example.com", email="bob@example.com", password="BobPass123!"
        )
        payload = {
            "current_password": "OldPass123!",
            "new_password": "NewPass456!",
            "confirm_password": "NewPass456!",
            "email": "bob@example.com",  # attempted injection, should be ignored
            "user_id": other_user.id,
        }
        response = self.client.post(self.url, payload, format='json', **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()
        other_user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewPass456!"))       # jane's password changed
        self.assertTrue(other_user.check_password("BobPass123!"))      # bob's password untouched

    def test_new_password_same_as_old_is_allowed(self):
        # boundary: not disallowed by current design — documents current behavior
        payload = {
            "current_password": "OldPass123!",
            "new_password": "OldPass123!",
            "confirm_password": "OldPass123!",
        }
        response = self.client.post(self.url, payload, format='json', **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_inactive_user_cannot_authenticate_to_change_password(self):
        # edge case: pending/unapproved users have no valid JWT session in practice,
        # but if a token were somehow issued, SimpleJWT still checks is_active on use
        self.user.is_active = False
        self.user.save(update_fields=['is_active'])
        payload = {
            "current_password": "OldPass123!",
            "new_password": "NewPass456!",
            "confirm_password": "NewPass456!",
        }
        response = self.client.post(self.url, payload, format='json', **self.headers)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

# ---------------------------------------------------------
# Approve user (superuser action, sends approval email)
# ---------------------------------------------------------

@override_settings(CACHES=TEST_CACHES, EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class ApproveUserViewTests(APITestCase):
    def setUp(self):
        cache.clear()
        mail.outbox = []
        self.url = reverse('approve-user')

        self.superuser = User.objects.create_superuser(
            username="root@example.com", email="root@example.com", password="RootPass123!"
        )
        self.pending_user = User.objects.create_user(
            username="pending@example.com",
            email="pending@example.com",
            password="PendingPass123!",
            is_active=False,
        )
        Profile.objects.create(
            user=self.pending_user, phone_number="+2348000000000", date_of_birth="1990-01-01"
        )

    # ---------- positive ----------

    def test_superuser_can_approve_pending_user(self):
        headers = get_auth_headers(self.superuser)
        response = self.client.post(self.url, {"user_id": self.pending_user.id}, format='json', **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.pending_user.refresh_from_db()
        self.assertTrue(self.pending_user.is_active)

    def test_approval_sends_email_to_approved_user(self):
        headers = get_auth_headers(self.superuser)
        self.client.post(self.url, {"user_id": self.pending_user.id}, format='json', **headers)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("pending@example.com", mail.outbox[0].to)
        self.assertIn("approved", mail.outbox[0].subject.lower())

    # ---------- negative ----------

    def test_non_superuser_cannot_approve(self):
        headers = get_auth_headers(self.pending_user)  # not even active, definitely not staff
        response = self.client.post(self.url, {"user_id": self.pending_user.id}, format='json', **headers)
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_staff_but_not_superuser_cannot_approve(self):
        staff = User.objects.create_user(
            username="staff@example.com", email="staff@example.com",
            password="StaffPass123!", is_active=True, is_staff=True,
        )
        headers = get_auth_headers(staff)
        response = self.client.post(self.url, {"user_id": self.pending_user.id}, format='json', **headers)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_approve(self):
        response = self.client.post(self.url, {"user_id": self.pending_user.id}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_nonexistent_user_id_returns_400(self):
        headers = get_auth_headers(self.superuser)
        response = self.client.post(self.url, {"user_id": 999999}, format='json', **headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_approving_already_active_user_returns_400(self):
        headers = get_auth_headers(self.superuser)
        active_user = User.objects.create_user(
            username="active@example.com", email="active@example.com",
            password="ActivePass123!", is_active=True,
        )
        response = self.client.post(self.url, {"user_id": active_user.id}, format='json', **headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(len(mail.outbox), 0)  # no email sent on failure

    # ---------- boundary / edge ----------

    def test_double_approval_second_attempt_fails(self):
        headers = get_auth_headers(self.superuser)
        self.client.post(self.url, {"user_id": self.pending_user.id}, format='json', **headers)
        response = self.client.post(self.url, {"user_id": self.pending_user.id}, format='json', **headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(len(mail.outbox), 1)  # only the first approval sent an email

    def test_missing_user_id_returns_400(self):
        headers = get_auth_headers(self.superuser)
        response = self.client.post(self.url, {}, format='json', **headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

# ---------------------------------------------------------
# Login (JWT token obtain)
# ---------------------------------------------------------

@override_settings(CACHES=TEST_CACHES)
class LoginViewTests(APITestCase):
    def setUp(self):
        self.url = reverse('login')
        self.user = User.objects.create_user(
            username="jane@example.com",
            email="jane@example.com",
            password="StrongPass123!",
            is_active=True,
        )
        Profile.objects.create(
            user=self.user, phone_number="+2348012345678", date_of_birth="1995-04-12"
        )

    # ---------- positive ----------

    def test_correct_credentials_returns_tokens(self):
        response = self.client.post(
            self.url, {"username": "jane@example.com", "password": "StrongPass123!"}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    # ---------- negative ----------

    def test_wrong_password_returns_401(self):
        response = self.client.post(
            self.url, {"username": "jane@example.com", "password": "WrongPass!"}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_nonexistent_user_returns_401(self):
        response = self.client.post(
            self.url, {"username": "ghost@example.com", "password": "Whatever123!"}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_missing_password_returns_400(self):
        response = self.client.post(self.url, {"username": "jane@example.com"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_empty_payload_returns_400(self):
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ---------- boundary / edge ----------

    def test_inactive_user_cannot_login(self):
        # covers: verified-but-not-yet-admin-approved users
        self.user.is_active = False
        self.user.save(update_fields=['is_active'])
        response = self.client.post(
            self.url, {"username": "jane@example.com", "password": "StrongPass123!"}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_case_sensitive_password(self):
        # boundary: passwords must be exact-case, "strongpass123!" should fail
        response = self.client.post(
            self.url, {"username": "jane@example.com", "password": "strongpass123!"}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ---------------------------------------------------------
# Logout (JWT token blacklist)
# ---------------------------------------------------------

@override_settings(CACHES=TEST_CACHES)
class LogoutViewTests(APITestCase):
    def setUp(self):
        self.url = reverse('logout')
        self.user = User.objects.create_user(
            username="jane@example.com",
            email="jane@example.com",
            password="StrongPass123!",
            is_active=True,
        )
        Profile.objects.create(
            user=self.user, phone_number="+2348012345678", date_of_birth="1995-04-12"
        )
        self.refresh = RefreshToken.for_user(self.user)
        self.access_headers = {"HTTP_AUTHORIZATION": f"Bearer {self.refresh.access_token}"}

    # ---------- positive ----------

    def test_valid_refresh_token_logs_out_successfully(self):
        response = self.client.post(
            self.url, {"refresh": str(self.refresh)}, format='json', **self.access_headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_blacklisted_refresh_token_cannot_be_reused(self):
        # log out once
        self.client.post(self.url, {"refresh": str(self.refresh)}, format='json', **self.access_headers)

        # try to use the same refresh token to get a new access token — must fail
        refresh_url = reverse('login-refresh')
        response = self.client.post(refresh_url, {"refresh": str(self.refresh)}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ---------- negative ----------

    def test_logout_without_authentication_returns_401(self):
        response = self.client.post(self.url, {"refresh": str(self.refresh)}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invalid_refresh_token_returns_400(self):
        response = self.client.post(
            self.url, {"refresh": "not-a-real-token"}, format='json', **self.access_headers
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_refresh_field_returns_400(self):
        response = self.client.post(self.url, {}, format='json', **self.access_headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ---------- boundary / edge ----------

    def test_double_logout_second_attempt_fails(self):
        # edge case: logging out with an already-blacklisted token should fail cleanly, not crash
        self.client.post(self.url, {"refresh": str(self.refresh)}, format='json', **self.access_headers)
        response = self.client.post(
            self.url, {"refresh": str(self.refresh)}, format='json', **self.access_headers
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logging_out_one_session_does_not_affect_another(self):
        # boundary: user has two active sessions (e.g. two devices); logging out one
        # should not invalidate the other
        second_refresh = RefreshToken.for_user(self.user)

        response = self.client.post(
            self.url, {"refresh": str(self.refresh)}, format='json', **self.access_headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        refresh_url = reverse('login-refresh')
        response2 = self.client.post(refresh_url, {"refresh": str(second_refresh)}, format='json')
        self.assertEqual(response2.status_code, status.HTTP_200_OK)  # second session still valid

