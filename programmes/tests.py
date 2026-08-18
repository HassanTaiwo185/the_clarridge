from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Programme
import io
from PIL import Image


def auth_headers(user):
    token = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {token.access_token}"}





def make_fake_image(name="cover.jpg"):
    """Generate a real, valid 1x1 pixel JPEG using Pillow, so ImageField validation passes."""
    buffer = io.BytesIO()
    image = Image.new("RGB", (1, 1), color="white")
    image.save(buffer, format="JPEG")
    buffer.seek(0)
    return SimpleUploadedFile(name, buffer.read(), content_type="image/jpeg")


class ProgrammePermissionTests(APITestCase):
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

        self.programme = Programme.objects.create(
            name="Test Programme",
            status=Programme.Status.UPCOMING,
            start_date="2026-01-01",
            end_date="2026-03-01",
            cover_image=make_fake_image(),
        )

        self.list_url = reverse('programme-list-create')
        self.detail_url = reverse('programme-detail', kwargs={'slug': self.programme.slug})

        self.valid_payload = {
            "name": "New Programme",
            "status": "open",
            "start_date": "2026-02-01",
            "end_date": "2026-04-01",
        }

    # =========================================================
    # READ (GET) — AllowAny, regardless of auth state
    # =========================================================

    def test_anonymous_can_list_programmes(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_anonymous_can_view_single_programme(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_regular_user_can_view_programme(self):
        response = self.client.get(self.detail_url, **auth_headers(self.regular_user))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_response_does_not_expose_creator_fields(self):
        # confirms created_by / created_at were correctly removed from the API surface
        response = self.client.get(self.detail_url)
        self.assertNotIn('created_by', response.data)
        self.assertNotIn('created_at', response.data)
        self.assertNotIn('updated_at', response.data)

    # =========================================================
    # CREATE (POST) — only staff or superuser
    # =========================================================

    def test_anonymous_cannot_create_programme(self):
        payload = {**self.valid_payload, "cover_image": make_fake_image()}
        response = self.client.post(self.list_url, payload, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_regular_authenticated_user_cannot_create_programme(self):
        payload = {**self.valid_payload, "cover_image": make_fake_image()}
        response = self.client.post(
            self.list_url, payload, format='multipart', **auth_headers(self.regular_user)
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_user_can_create_programme(self):
        payload = {**self.valid_payload, "cover_image": make_fake_image()}
        response = self.client.post(
            self.list_url, payload, format='multipart', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_superuser_can_create_programme(self):
        payload = {**self.valid_payload, "cover_image": make_fake_image()}
        response = self.client.post(
            self.list_url, payload, format='multipart', **auth_headers(self.superuser)
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_without_cover_image_returns_400(self):
        response = self.client.post(
            self.list_url, self.valid_payload, format='multipart', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cover_image", response.data)

    def test_create_without_dates_returns_400(self):
        payload = {"name": "No Dates", "status": "open", "cover_image": make_fake_image()}
        response = self.client.post(
            self.list_url, payload, format='multipart', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("start_date", response.data)
        self.assertIn("end_date", response.data)

    def test_create_with_invalid_status_returns_400(self):
        payload = {**self.valid_payload, "status": "cancelled", "cover_image": make_fake_image()}
        response = self.client.post(
            self.list_url, payload, format='multipart', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("status", response.data)

    def test_create_with_end_date_before_start_date_returns_400(self):
        payload = {
            "name": "Backwards Programme",
            "status": "open",
            "start_date": "2026-05-01",
            "end_date": "2026-01-01",
            "cover_image": make_fake_image(),
        }
        response = self.client.post(
            self.list_url, payload, format='multipart', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("end_date", response.data)

    def test_create_with_end_date_equal_to_start_date_is_allowed(self):
        # boundary: single-day programme, start == end should be valid, not an error
        payload = {
            "name": "One Day Programme",
            "status": "open",
            "start_date": "2026-06-01",
            "end_date": "2026-06-01",
            "cover_image": make_fake_image(),
        }
        response = self.client.post(
            self.list_url, payload, format='multipart', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_status_defaults_to_upcoming_if_not_provided(self):
        payload = {
            "name": "Default Status Programme",
            "start_date": "2026-07-01",
            "end_date": "2026-08-01",
            "cover_image": make_fake_image(),
        }
        response = self.client.post(
            self.list_url, payload, format='multipart', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'upcoming')

    def test_slug_is_auto_generated_and_read_only(self):
        payload = {**self.valid_payload, "slug": "hacked-slug", "cover_image": make_fake_image()}
        response = self.client.post(
            self.list_url, payload, format='multipart', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotEqual(response.data['slug'], 'hacked-slug')
        self.assertEqual(response.data['slug'], 'new-programme')

    def test_duplicate_name_generates_unique_slug(self):
        # boundary: two programmes with the same name must not collide on slug
        payload = {
            "name": "Test Programme",  # same name as self.programme
            "status": "open",
            "start_date": "2026-09-01",
            "end_date": "2026-10-01",
            "cover_image": make_fake_image(),
        }
        response = self.client.post(
            self.list_url, payload, format='multipart', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotEqual(response.data['slug'], self.programme.slug)
        self.assertEqual(response.data['slug'], 'test-programme-1')

    # =========================================================
    # UPDATE (PATCH) — only staff or superuser
    # =========================================================

    def test_anonymous_cannot_update_programme(self):
        response = self.client.patch(self.detail_url, {"name": "Hacked"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_regular_user_cannot_update_programme(self):
        response = self.client.patch(
            self.detail_url, {"name": "Hacked"}, format='json', **auth_headers(self.regular_user)
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.programme.refresh_from_db()
        self.assertEqual(self.programme.name, "Test Programme")

    def test_staff_user_can_update_programme(self):
        response = self.client.patch(
            self.detail_url, {"name": "Updated Name"}, format='json', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.programme.refresh_from_db()
        self.assertEqual(self.programme.name, "Updated Name")

    def test_superuser_can_update_programme(self):
        response = self.client.patch(
            self.detail_url, {"status": "completed"}, format='json', **auth_headers(self.superuser)
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.programme.refresh_from_db()
        self.assertEqual(self.programme.status, "completed")

    def test_update_with_end_date_before_start_date_returns_400(self):
        response = self.client.patch(
            self.detail_url,
            {"end_date": "2025-01-01"},  # before existing start_date of 2026-01-01
            format='json', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_partial_update_only_status_does_not_require_other_fields(self):
        # boundary: PATCH should not force re-submission of cover_image/dates
        response = self.client.patch(
            self.detail_url, {"status": "open"}, format='json', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_slug_is_ignored(self):
        response = self.client.patch(
            self.detail_url, {"slug": "hacked-slug"}, format='json', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.programme.refresh_from_db()
        self.assertNotEqual(self.programme.slug, "hacked-slug")

    # =========================================================
    # DELETE — only staff or superuser
    # =========================================================

    def test_anonymous_cannot_delete_programme(self):
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_regular_user_cannot_delete_programme(self):
        response = self.client.delete(self.detail_url, **auth_headers(self.regular_user))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Programme.objects.filter(id=self.programme.id).exists())

    def test_staff_user_can_delete_programme(self):
        response = self.client.delete(self.detail_url, **auth_headers(self.staff_user))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Programme.objects.filter(id=self.programme.id).exists())

    def test_superuser_can_delete_programme(self):
        response = self.client.delete(self.detail_url, **auth_headers(self.superuser))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Programme.objects.filter(id=self.programme.id).exists())

    # =========================================================
    # BOUNDARY / EDGE CASES
    # =========================================================

    def test_deactivated_staff_user_cannot_write(self):
        self.staff_user.is_active = False
        self.staff_user.save(update_fields=['is_active'])
        response = self.client.patch(
            self.detail_url, {"name": "Should Fail"}, format='json', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_updating_nonexistent_programme_returns_404(self):
        bad_url = reverse('programme-detail', kwargs={'slug': 'does-not-exist'})
        response = self.client.patch(
            bad_url, {"name": "Ghost"}, format='json', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_deleting_nonexistent_programme_returns_404(self):
        bad_url = reverse('programme-detail', kwargs={'slug': 'does-not-exist'})
        response = self.client.delete(bad_url, **auth_headers(self.staff_user))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_empty_name_returns_400(self):
        payload = {
            "name": "",
            "status": "open",
            "start_date": "2026-01-01",
            "end_date": "2026-02-01",
            "cover_image": make_fake_image(),
        }
        response = self.client.post(
            self.list_url, payload, format='multipart', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_date_format_returns_400(self):
        payload = {
            "name": "Bad Date Programme",
            "status": "open",
            "start_date": "not-a-date",
            "end_date": "2026-02-01",
            "cover_image": make_fake_image(),
        }
        response = self.client.post(
            self.list_url, payload, format='multipart', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("start_date", response.data)

    def test_description_is_optional(self):
        payload = {**self.valid_payload, "cover_image": make_fake_image()}
        response = self.client.post(
            self.list_url, payload, format='multipart', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['description'], '')