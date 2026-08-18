import io
from PIL import Image
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Application


def auth_headers(user):
    token = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {token.access_token}"}


def make_fake_image(name="photo.jpg"):
    buffer = io.BytesIO()
    image = Image.new("RGB", (1, 1), color="white")
    image.save(buffer, format="JPEG")
    buffer.seek(0)
    return SimpleUploadedFile(name, buffer.read(), content_type="image/jpeg")


def make_fake_pdf(name="transcript.pdf"):
    return SimpleUploadedFile(name, b"%PDF-1.4 fake pdf content", content_type="application/pdf")


def make_oversized_file(name="huge.pdf", size_mb=6):
    content = b"x" * (size_mb * 1024 * 1024)
    return SimpleUploadedFile(name, content, content_type="application/pdf")


class ApplicationPermissionTests(APITestCase):
    def setUp(self):
        self.regular_user = User.objects.create_user(
            username="user@example.com", email="user@example.com",
            password="UserPass123!", is_active=True,
        )
        self.staff_user = User.objects.create_user(
            username="staff@example.com", email="staff@example.com",
            password="StaffPass123!", is_active=True, is_staff=True,
        )
        self.superuser = User.objects.create_superuser(
            username="root@example.com", email="root@example.com", password="RootPass123!"
        )

        self.application = Application.objects.create(
            full_name="Jane Applicant",
            email="jane.applicant@example.com",
            phone_number="+2348012345678",
            date_of_birth="1998-05-15",
            passport_photo=make_fake_image(),
            cv_transcript=make_fake_pdf(),
        )

        self.list_url = reverse('application-list-create')
        self.detail_url = reverse('application-detail', kwargs={'pk': self.application.pk})

        self.valid_payload = {
            "full_name": "John New Applicant",
            "email": "john.new@example.com",
            "phone_number": "+2348099999999",
            "date_of_birth": "1999-01-01",
        }

    # =========================================================
    # CREATE (POST) — public, anyone can submit
    # =========================================================

    def test_anonymous_can_submit_application(self):
        payload = {
            **self.valid_payload,
            "passport_photo": make_fake_image(),
            "cv_transcript": make_fake_pdf(),
        }
        response = self.client.post(self.list_url, payload, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_authenticated_user_can_also_submit_application(self):
        payload = {
            **self.valid_payload,
            "passport_photo": make_fake_image(),
            "cv_transcript": make_fake_pdf(),
        }
        response = self.client.post(
            self.list_url, payload, format='multipart', **auth_headers(self.regular_user)
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_new_application_defaults_to_pending(self):
        payload = {
            **self.valid_payload,
            "passport_photo": make_fake_image(),
            "cv_transcript": make_fake_pdf(),
        }
        self.client.post(self.list_url, payload, format='multipart')
        new_app = Application.objects.get(email="john.new@example.com")
        self.assertEqual(new_app.status, "pending")

    def test_applicant_cannot_set_own_status(self):
        # edge case: status field isn't exposed on the public create serializer
        payload = {
            **self.valid_payload,
            "status": "approved",
            "passport_photo": make_fake_image(),
            "cv_transcript": make_fake_pdf(),
        }
        response = self.client.post(self.list_url, payload, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        new_app = Application.objects.get(email="john.new@example.com")
        self.assertEqual(new_app.status, "pending")  # ignored, still defaults to pending

    def test_create_without_passport_photo_returns_400(self):
        payload = {**self.valid_payload, "cv_transcript": make_fake_pdf()}
        response = self.client.post(self.list_url, payload, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("passport_photo", response.data)

    def test_create_without_cv_transcript_returns_400(self):
        payload = {**self.valid_payload, "passport_photo": make_fake_image()}
        response = self.client.post(self.list_url, payload, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cv_transcript", response.data)

    def test_create_without_email_returns_400(self):
        payload = {
            "full_name": "No Email",
            "phone_number": "+2348000000000",
            "date_of_birth": "2000-01-01",
            "passport_photo": make_fake_image(),
            "cv_transcript": make_fake_pdf(),
        }
        response = self.client.post(self.list_url, payload, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_invalid_email_format_returns_400(self):
        payload = {
            **self.valid_payload, "email": "not-an-email",
            "passport_photo": make_fake_image(), "cv_transcript": make_fake_pdf(),
        }
        response = self.client.post(self.list_url, payload, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_invalid_date_of_birth_format_returns_400(self):
        payload = {
            **self.valid_payload, "date_of_birth": "not-a-date",
            "passport_photo": make_fake_image(), "cv_transcript": make_fake_pdf(),
        }
        response = self.client.post(self.list_url, payload, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("date_of_birth", response.data)

    def test_passport_photo_wrong_extension_returns_400(self):
        bad_photo = SimpleUploadedFile("photo.gif", b"gif content", content_type="image/gif")
        payload = {**self.valid_payload, "passport_photo": bad_photo, "cv_transcript": make_fake_pdf()}
        response = self.client.post(self.list_url, payload, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("passport_photo", response.data)

    def test_cv_transcript_wrong_extension_returns_400(self):
        bad_cv = SimpleUploadedFile("cv.docx", b"docx content", content_type="application/msword")
        payload = {**self.valid_payload, "passport_photo": make_fake_image(), "cv_transcript": bad_cv}
        response = self.client.post(self.list_url, payload, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cv_transcript", response.data)

    def test_oversized_cv_transcript_returns_400(self):
        # boundary: > 5MB must be rejected
        big_file = make_oversized_file(size_mb=6)
        payload = {**self.valid_payload, "passport_photo": make_fake_image(), "cv_transcript": big_file}
        response = self.client.post(self.list_url, payload, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cv_transcript", response.data)

    def test_png_passport_photo_is_accepted(self):
        buffer = io.BytesIO()
        Image.new("RGB", (1, 1), color="blue").save(buffer, format="PNG")
        buffer.seek(0)
        png_photo = SimpleUploadedFile("photo.png", buffer.read(), content_type="image/png")
        payload = {**self.valid_payload, "passport_photo": png_photo, "cv_transcript": make_fake_pdf()}
        response = self.client.post(self.list_url, payload, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_duplicate_email_applications_are_allowed(self):
        # boundary: no uniqueness constraint on email — same person can apply twice
        payload = {
            **self.valid_payload, "email": self.application.email,
            "passport_photo": make_fake_image(), "cv_transcript": make_fake_pdf(),
        }
        response = self.client.post(self.list_url, payload, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Application.objects.filter(email=self.application.email).count(), 2)

    # =========================================================
    # LIST/VIEW (GET) — admin/superuser only, public has NO read access
    # =========================================================

    def test_anonymous_cannot_list_applications(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_anonymous_cannot_view_single_application(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_regular_authenticated_user_cannot_list_applications(self):
        response = self.client.get(self.list_url, **auth_headers(self.regular_user))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_regular_authenticated_user_cannot_view_single_application(self):
        response = self.client.get(self.detail_url, **auth_headers(self.regular_user))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_user_can_list_applications(self):
        response = self.client.get(self.list_url, **auth_headers(self.staff_user))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_staff_user_can_view_single_application(self):
        response = self.client.get(self.detail_url, **auth_headers(self.staff_user))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_superuser_can_list_applications(self):
        response = self.client.get(self.list_url, **auth_headers(self.superuser))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_view_includes_status_and_date_applied(self):
        response = self.client.get(self.detail_url, **auth_headers(self.staff_user))
        self.assertIn("status", response.data)
        self.assertIn("date_applied", response.data)

    # =========================================================
    # UPDATE (PATCH — status changes) — admin/superuser only
    # =========================================================

    def test_anonymous_cannot_update_status(self):
        response = self.client.patch(self.detail_url, {"status": "shortlisted"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_regular_user_cannot_update_status(self):
        response = self.client.patch(
            self.detail_url, {"status": "shortlisted"}, format='json', **auth_headers(self.regular_user)
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, "pending")

    def test_staff_user_can_shortlist_application(self):
        response = self.client.patch(
            self.detail_url, {"status": "shortlisted"}, format='json', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, "shortlisted")

    def test_staff_user_can_approve_application(self):
        response = self.client.patch(
            self.detail_url, {"status": "approved"}, format='json', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, "approved")

    def test_superuser_can_update_status(self):
        response = self.client.patch(
            self.detail_url, {"status": "shortlisted"}, format='json', **auth_headers(self.superuser)
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_invalid_status_value_returns_400(self):
        response = self.client.patch(
            self.detail_url, {"status": "rejected"}, format='json', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_date_applied_cannot_be_modified(self):
        # edge case: date_applied is read-only, must not change via PATCH
        original_date = self.application.date_applied
        self.client.patch(
            self.detail_url, {"date_applied": "2020-01-01T00:00:00Z"}, format='json',
            **auth_headers(self.staff_user)
        )
        self.application.refresh_from_db()
        self.assertEqual(self.application.date_applied, original_date)

    def test_status_can_be_set_directly_to_approved_skipping_shortlisted(self):
        # documents current behavior: no enforced pending -> shortlisted -> approved sequence
        response = self.client.patch(
            self.detail_url, {"status": "approved"}, format='json', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, "approved")

    def test_status_can_be_moved_backward(self):
        # documents current behavior: no restriction preventing approved -> pending
        self.application.status = "approved"
        self.application.save(update_fields=['status'])
        response = self.client.patch(
            self.detail_url, {"status": "pending"}, format='json', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, "pending")

    # =========================================================
    # DELETE — admin/superuser only
    # =========================================================

    def test_anonymous_cannot_delete_application(self):
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_regular_user_cannot_delete_application(self):
        response = self.client.delete(self.detail_url, **auth_headers(self.regular_user))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Application.objects.filter(id=self.application.id).exists())

    def test_staff_user_can_delete_application(self):
        response = self.client.delete(self.detail_url, **auth_headers(self.staff_user))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Application.objects.filter(id=self.application.id).exists())

    def test_superuser_can_delete_application(self):
        response = self.client.delete(self.detail_url, **auth_headers(self.superuser))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Application.objects.filter(id=self.application.id).exists())

    # =========================================================
    # BOUNDARY / EDGE CASES
    # =========================================================

    def test_deactivated_staff_user_cannot_manage(self):
        self.staff_user.is_active = False
        self.staff_user.save(update_fields=['is_active'])
        response = self.client.get(self.list_url, **auth_headers(self.staff_user))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_updating_nonexistent_application_returns_404(self):
        bad_url = reverse('application-detail', kwargs={'pk': 999999})
        response = self.client.patch(
            bad_url, {"status": "approved"}, format='json', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_deleting_nonexistent_application_returns_404(self):
        bad_url = reverse('application-detail', kwargs={'pk': 999999})
        response = self.client.delete(bad_url, **auth_headers(self.staff_user))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_view_reflects_multiple_applications(self):
        Application.objects.create(
            full_name="Second Applicant", email="second@example.com",
            phone_number="+2348011111111", date_of_birth="1997-03-03",
            passport_photo=make_fake_image("p2.jpg"), cv_transcript=make_fake_pdf("cv2.pdf"),
        )
        response = self.client.get(self.list_url, **auth_headers(self.staff_user))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)