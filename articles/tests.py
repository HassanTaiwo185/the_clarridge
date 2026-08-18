from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Article


def auth_headers(user):
    token = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {token.access_token}"}


def make_fake_pdf(name="test.pdf"):
    return SimpleUploadedFile(name, b"%PDF-1.4 fake pdf content", content_type="application/pdf")


class ArticlePermissionTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="owner@example.com", email="owner@example.com",
            password="OwnerPass123!", is_active=True,
        )
        self.other_user = User.objects.create_user(
            username="other@example.com", email="other@example.com",
            password="OtherPass123!", is_active=True,
        )
        self.superuser = User.objects.create_superuser(
            username="root@example.com", email="root@example.com", password="RootPass123!"
        )
        self.staff_non_super = User.objects.create_user(
            username="staff@example.com", email="staff@example.com",
            password="StaffPass123!", is_active=True, is_staff=True,
        )

        self.article = Article.objects.create(
            uploaded_by=self.owner,
            title="Test Article",
            author_name="Some Writer",
            summary="A short summary.",
            date_written="2024-01-01",
            pdf_file=make_fake_pdf(),
        )

        self.list_url = reverse('article-list-create')
        self.detail_url = reverse('article-detail', kwargs={'slug': self.article.slug})

        self.valid_payload = {
            "title": "New Article",
            "author_name": "Jane Writer",
            "summary": "Summary text.",
            "date_written": "2024-05-01",
        }
        self.update_payload = {"title": "Updated Title"}

    # =========================================================
    # READ (GET) — must be AllowAny, regardless of auth state
    # =========================================================

    def test_anonymous_can_list_articles(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_anonymous_can_view_single_article(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_authenticated_non_owner_can_view_article(self):
        response = self.client.get(self.detail_url, **auth_headers(self.other_user))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_owner_can_view_own_article(self):
        response = self.client.get(self.detail_url, **auth_headers(self.owner))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # =========================================================
    # CREATE (POST) — must be authenticated, any authenticated user allowed
    # =========================================================

    def test_anonymous_cannot_create_article(self):
        payload = {**self.valid_payload, "pdf_file": make_fake_pdf()}
        response = self.client.post(self.list_url, payload, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_user_can_create_article(self):
        payload = {**self.valid_payload, "pdf_file": make_fake_pdf()}
        response = self.client.post(
            self.list_url, payload, format='multipart', **auth_headers(self.other_user)
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_created_article_uploaded_by_is_forced_to_requesting_user(self):
        # edge case: even if client tries to spoof uploaded_by, it must be ignored
        payload = {**self.valid_payload, "uploaded_by": self.owner.id, "pdf_file": make_fake_pdf()}
        response = self.client.post(
            self.list_url, payload, format='multipart', **auth_headers(self.other_user)
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        new_article = Article.objects.get(title="New Article")
        self.assertEqual(new_article.uploaded_by, self.other_user)  # not self.owner

    def test_superuser_can_create_article(self):
        payload = {**self.valid_payload, "pdf_file": make_fake_pdf()}
        response = self.client.post(
            self.list_url, payload, format='multipart', **auth_headers(self.superuser)
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_without_pdf_file_returns_400(self):
        # boundary: pdf_file is required, must fail cleanly without one
        response = self.client.post(
            self.list_url, self.valid_payload, format='multipart', **auth_headers(self.owner)
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("pdf_file", response.data)

    def test_create_with_non_pdf_file_returns_400(self):
        # edge case: wrong file type should be rejected by the extension validator
        fake_txt = SimpleUploadedFile("test.txt", b"not a pdf", content_type="text/plain")
        payload = {**self.valid_payload, "pdf_file": fake_txt}
        response = self.client.post(
            self.list_url, payload, format='multipart', **auth_headers(self.owner)
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # =========================================================
    # UPDATE (PATCH) — only owner or superuser
    # =========================================================

    def test_owner_can_update_own_article(self):
        response = self.client.patch(
            self.detail_url, self.update_payload, format='json', **auth_headers(self.owner)
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.article.refresh_from_db()
        self.assertEqual(self.article.title, "Updated Title")

    def test_non_owner_cannot_update_article(self):
        response = self.client.patch(
            self.detail_url, self.update_payload, format='json', **auth_headers(self.other_user)
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.article.refresh_from_db()
        self.assertEqual(self.article.title, "Test Article")  # unchanged

    def test_superuser_can_update_any_article(self):
        response = self.client.patch(
            self.detail_url, self.update_payload, format='json', **auth_headers(self.superuser)
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.article.refresh_from_db()
        self.assertEqual(self.article.title, "Updated Title")

    def test_staff_non_superuser_cannot_update_others_article(self):
        # edge case: is_staff alone must NOT be enough — only true superuser or owner
        response = self.client.patch(
            self.detail_url, self.update_payload, format='json', **auth_headers(self.staff_non_super)
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_cannot_update_article(self):
        response = self.client.patch(self.detail_url, self.update_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # =========================================================
    # DELETE — only owner or superuser
    # =========================================================

    def test_owner_can_delete_own_article(self):
        response = self.client.delete(self.detail_url, **auth_headers(self.owner))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Article.objects.filter(id=self.article.id).exists())

    def test_non_owner_cannot_delete_article(self):
        response = self.client.delete(self.detail_url, **auth_headers(self.other_user))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Article.objects.filter(id=self.article.id).exists())

    def test_superuser_can_delete_any_article(self):
        response = self.client.delete(self.detail_url, **auth_headers(self.superuser))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Article.objects.filter(id=self.article.id).exists())

    def test_staff_non_superuser_cannot_delete_others_article(self):
        response = self.client.delete(self.detail_url, **auth_headers(self.staff_non_super))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Article.objects.filter(id=self.article.id).exists())

    def test_anonymous_cannot_delete_article(self):
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # =========================================================
    # BOUNDARY / EDGE CASES
    # =========================================================

    def test_owner_cannot_edit_after_being_deactivated(self):
        # edge case: an inactive account has no valid session, even if they were the owner
        self.owner.is_active = False
        self.owner.save(update_fields=['is_active'])
        response = self.client.patch(
            self.detail_url, self.update_payload, format='json', **auth_headers(self.owner)
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_updating_nonexistent_article_returns_404(self):
        bad_url = reverse('article-detail', kwargs={'slug': 'does-not-exist'})
        response = self.client.patch(
            bad_url, self.update_payload, format='json', **auth_headers(self.owner)
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_ownership_transfer_is_not_possible_via_update(self):
        # edge case: owner tries to reassign uploaded_by to someone else via PATCH — must be ignored
        payload = {"uploaded_by": self.other_user.id}
        response = self.client.patch(
            self.detail_url, payload, format='json', **auth_headers(self.owner)
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.article.refresh_from_db()
        self.assertEqual(self.article.uploaded_by, self.owner)  # unchanged, still owner

    def test_second_owner_of_different_article_cannot_touch_first_owners_article(self):
        # boundary: being *an* owner of *some* article doesn't grant access to *another's* article
        other_article = Article.objects.create(
            uploaded_by=self.other_user,
            title="Other Article",
            author_name="Other Writer",
            summary="Another summary.",
            date_written="2024-02-01",
            pdf_file=make_fake_pdf("other.pdf"),
        )
        other_detail_url = reverse('article-detail', kwargs={'slug': other_article.slug})

        # owner (of self.article) tries to delete other_user's separate article
        response = self.client.delete(other_detail_url, **auth_headers(self.owner))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)