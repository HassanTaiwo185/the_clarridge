import io
from PIL import Image
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from .models import CollegiumMember


def auth_headers(user):
    token = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {token.access_token}"}


def make_fake_image(name="photo.jpg"):
    buffer = io.BytesIO()
    image = Image.new("RGB", (1, 1), color="white")
    image.save(buffer, format="JPEG")
    buffer.seek(0)
    return SimpleUploadedFile(name, buffer.read(), content_type="image/jpeg")


class CollegiumMemberPermissionTests(APITestCase):
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

        self.member = CollegiumMember.objects.create(
            member_name="Dr. Jane Smith",
            photo=make_fake_image(),
            school="University of Lagos",
            field="Computer Science",
        )

        self.list_url = reverse('collegium-list-create')
        self.detail_url = reverse('collegium-detail', kwargs={'pk': self.member.pk})

        self.valid_payload = {
            "member_name": "Dr. John Doe",
            "school": "University of Ibadan",
            "field": "Physics",
        }

    # =========================================================
    # READ (GET) — AllowAny, regardless of auth state
    # =========================================================

    def test_anonymous_can_list_members(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_anonymous_can_view_single_member(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_regular_user_can_view_member(self):
        response = self.client.get(self.detail_url, **auth_headers(self.regular_user))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_returns_correct_fields(self):
        response = self.client.get(self.detail_url)
        for field in ['id', 'member_name', 'photo', 'school', 'field']:
            self.assertIn(field, response.data)

    # =========================================================
    # CREATE (POST) — only staff or superuser
    # =========================================================

    def test_anonymous_cannot_create_member(self):
        payload = {**self.valid_payload, "photo": make_fake_image()}
        response = self.client.post(self.list_url, payload, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_regular_authenticated_user_cannot_create_member(self):
        payload = {**self.valid_payload, "photo": make_fake_image()}
        response = self.client.post(
            self.list_url, payload, format='multipart', **auth_headers(self.regular_user)
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_user_can_create_member(self):
        payload = {**self.valid_payload, "photo": make_fake_image()}
        response = self.client.post(
            self.list_url, payload, format='multipart', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_superuser_can_create_member(self):
        payload = {**self.valid_payload, "photo": make_fake_image()}
        response = self.client.post(
            self.list_url, payload, format='multipart', **auth_headers(self.superuser)
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_without_photo_returns_400(self):
        response = self.client.post(
            self.list_url, self.valid_payload, format='multipart', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("photo", response.data)

    def test_create_with_invalid_image_returns_400(self):
        bad_file = SimpleUploadedFile("not-an-image.txt", b"just text", content_type="text/plain")
        payload = {**self.valid_payload, "photo": bad_file}
        response = self.client.post(
            self.list_url, payload, format='multipart', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("photo", response.data)

    def test_create_without_member_name_returns_400(self):
        payload = {"school": "Some School", "field": "Some Field", "photo": make_fake_image()}
        response = self.client.post(
            self.list_url, payload, format='multipart', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("member_name", response.data)

    def test_create_without_school_returns_400(self):
        payload = {"member_name": "No School", "field": "Some Field", "photo": make_fake_image()}
        response = self.client.post(
            self.list_url, payload, format='multipart', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("school", response.data)

    def test_create_without_field_returns_400(self):
        payload = {"member_name": "No Field", "school": "Some School", "photo": make_fake_image()}
        response = self.client.post(
            self.list_url, payload, format='multipart', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("field", response.data)

    def test_empty_member_name_returns_400(self):
        payload = {**self.valid_payload, "member_name": "", "photo": make_fake_image()}
        response = self.client.post(
            self.list_url, payload, format='multipart', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # =========================================================
    # UPDATE (PATCH) — only staff or superuser
    # =========================================================

    def test_anonymous_cannot_update_member(self):
        response = self.client.patch(self.detail_url, {"member_name": "Hacked"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_regular_user_cannot_update_member(self):
        response = self.client.patch(
            self.detail_url, {"member_name": "Hacked"}, format='json', **auth_headers(self.regular_user)
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.member.refresh_from_db()
        self.assertEqual(self.member.member_name, "Dr. Jane Smith")

    def test_staff_user_can_update_member(self):
        response = self.client.patch(
            self.detail_url, {"member_name": "Dr. Jane Updated"}, format='json', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.member.refresh_from_db()
        self.assertEqual(self.member.member_name, "Dr. Jane Updated")

    def test_superuser_can_update_member(self):
        response = self.client.patch(
            self.detail_url, {"field": "Mathematics"}, format='json', **auth_headers(self.superuser)
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.member.refresh_from_db()
        self.assertEqual(self.member.field, "Mathematics")

    def test_partial_update_does_not_require_photo(self):
        # boundary: PATCH shouldn't force re-uploading the photo just to change a name
        response = self.client.patch(
            self.detail_url, {"member_name": "Just A Name Change"}, format='json', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_can_change_photo(self):
        response = self.client.patch(
            self.detail_url, {"photo": make_fake_image("new.jpg")}, format='multipart', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # =========================================================
    # DELETE — only staff or superuser
    # =========================================================

    def test_anonymous_cannot_delete_member(self):
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_regular_user_cannot_delete_member(self):
        response = self.client.delete(self.detail_url, **auth_headers(self.regular_user))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(CollegiumMember.objects.filter(id=self.member.id).exists())

    def test_staff_user_can_delete_member(self):
        response = self.client.delete(self.detail_url, **auth_headers(self.staff_user))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CollegiumMember.objects.filter(id=self.member.id).exists())

    def test_superuser_can_delete_member(self):
        response = self.client.delete(self.detail_url, **auth_headers(self.superuser))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CollegiumMember.objects.filter(id=self.member.id).exists())

    # =========================================================
    # BOUNDARY / EDGE CASES
    # =========================================================

    def test_deactivated_staff_user_cannot_write(self):
        self.staff_user.is_active = False
        self.staff_user.save(update_fields=['is_active'])
        response = self.client.patch(
            self.detail_url, {"member_name": "Should Fail"}, format='json', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_updating_nonexistent_member_returns_404(self):
        bad_url = reverse('collegium-detail', kwargs={'pk': 999999})
        response = self.client.patch(
            bad_url, {"member_name": "Ghost"}, format='json', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_deleting_nonexistent_member_returns_404(self):
        bad_url = reverse('collegium-detail', kwargs={'pk': 999999})
        response = self.client.delete(bad_url, **auth_headers(self.staff_user))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_two_members_can_have_same_name(self):
        # boundary: no uniqueness constraint on member_name — duplicates should be allowed
        payload = {
            "member_name": "Dr. Jane Smith",  # same name as self.member
            "school": "Different University",
            "field": "Chemistry",
            "photo": make_fake_image(),
        }
        response = self.client.post(
            self.list_url, payload, format='multipart', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CollegiumMember.objects.filter(member_name="Dr. Jane Smith").count(), 2)

    def test_list_view_after_creating_multiple_members(self):
        CollegiumMember.objects.create(
            member_name="Dr. Second Member", photo=make_fake_image("m2.jpg"),
            school="School B", field="Biology",
        )
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)