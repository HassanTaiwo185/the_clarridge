from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Testimonial


def auth_headers(user):
    token = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {token.access_token}"}


class TestimonialPermissionTests(APITestCase):
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

        self.pending_testimonial = Testimonial.objects.create(
            submitted_by="Ngozi Chukwu",
            programme="Internship Placement",
            content="This changed how I see my career.",
            status=Testimonial.Status.PENDING,
        )
        self.approved_testimonial = Testimonial.objects.create(
            submitted_by="Femi Adebayo",
            programme="Writing Fellowship",
            content="I never thought I could publish.",
            status=Testimonial.Status.APPROVED,
        )
        self.rejected_testimonial = Testimonial.objects.create(
            submitted_by="Bola Ahmed",
            programme="Research Grant",
            content="Not what I expected.",
            status=Testimonial.Status.REJECTED,
        )

        self.list_url = reverse('testimonial-list-create')
        self.detail_url = reverse('testimonial-detail', kwargs={'pk': self.pending_testimonial.pk})
        self.public_url = reverse('testimonial-public-list')

        self.valid_payload = {
            "submitted_by": "New Submitter",
            "programme": "Some Programme",
            "content": "Great experience overall.",
        }

    # =========================================================
    # PUBLIC ENDPOINT — approved-only, visible to everyone
    # =========================================================

    def test_anonymous_can_view_public_testimonials(self):
        response = self.client.get(self.public_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_public_endpoint_only_returns_approved(self):
        response = self.client.get(self.public_url)
        submitted_names = [t['submitted_by'] for t in response.data]
        self.assertIn("Femi Adebayo", submitted_names)
        self.assertNotIn("Ngozi Chukwu", submitted_names)   # pending
        self.assertNotIn("Bola Ahmed", submitted_names)     # rejected

    def test_public_endpoint_does_not_expose_status_field(self):
        response = self.client.get(self.public_url)
        for testimonial in response.data:
            self.assertNotIn('status', testimonial)

    def test_public_endpoint_hides_all_when_none_approved(self):
        Testimonial.objects.filter(status=Testimonial.Status.APPROVED).update(
            status=Testimonial.Status.PENDING
        )
        response = self.client.get(self.public_url)
        self.assertEqual(len(response.data), 0)

    def test_authenticated_regular_user_can_also_view_public_testimonials(self):
        response = self.client.get(self.public_url, **auth_headers(self.regular_user))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # =========================================================
    # CREATE (POST) — public submission, always defaults to pending
    # =========================================================

    def test_anonymous_can_submit_testimonial(self):
        response = self.client.post(self.list_url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_new_testimonial_defaults_to_pending(self):
        self.client.post(self.list_url, self.valid_payload, format='json')
        new_t = Testimonial.objects.get(submitted_by="New Submitter")
        self.assertEqual(new_t.status, "pending")

    def test_submitter_cannot_set_own_status(self):
        # edge case: status not exposed on public create serializer
        payload = {**self.valid_payload, "status": "approved"}
        response = self.client.post(self.list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        new_t = Testimonial.objects.get(submitted_by="New Submitter")
        self.assertEqual(new_t.status, "pending")  # ignored

    def test_new_testimonial_not_visible_on_public_endpoint_immediately(self):
        self.client.post(self.list_url, self.valid_payload, format='json')
        response = self.client.get(self.public_url)
        names = [t['submitted_by'] for t in response.data]
        self.assertNotIn("New Submitter", names)

    def test_create_without_submitted_by_returns_400(self):
        payload = {"programme": "Some Programme", "content": "Text"}
        response = self.client.post(self.list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("submitted_by", response.data)

    def test_create_without_programme_returns_400(self):
        payload = {"submitted_by": "Someone", "content": "Text"}
        response = self.client.post(self.list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("programme", response.data)

    def test_create_without_content_returns_400(self):
        payload = {"submitted_by": "Someone", "programme": "Some Programme"}
        response = self.client.post(self.list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("content", response.data)

    def test_empty_content_returns_400(self):
        payload = {**self.valid_payload, "content": ""}
        response = self.client.post(self.list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_authenticated_user_can_also_submit(self):
        response = self.client.post(
            self.list_url, self.valid_payload, format='json', **auth_headers(self.regular_user)
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    # =========================================================
    # ADMIN LIST/VIEW (GET on management endpoint) — staff/superuser only
    # =========================================================

    def test_anonymous_cannot_list_all_testimonials(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_regular_user_cannot_list_all_testimonials(self):
        response = self.client.get(self.list_url, **auth_headers(self.regular_user))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_can_list_all_testimonials_including_pending_and_rejected(self):
        response = self.client.get(self.list_url, **auth_headers(self.staff_user))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [t['submitted_by'] for t in response.data]
        self.assertIn("Ngozi Chukwu", names)   # pending
        self.assertIn("Femi Adebayo", names)   # approved
        self.assertIn("Bola Ahmed", names)     # rejected

    def test_superuser_can_list_all_testimonials(self):
        response = self.client.get(self.list_url, **auth_headers(self.superuser))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

    def test_admin_list_includes_status_field(self):
        response = self.client.get(self.list_url, **auth_headers(self.staff_user))
        for t in response.data:
            self.assertIn('status', t)

    def test_anonymous_cannot_view_single_testimonial_via_admin_endpoint(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_regular_user_cannot_view_single_testimonial_via_admin_endpoint(self):
        response = self.client.get(self.detail_url, **auth_headers(self.regular_user))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_can_view_single_testimonial(self):
        response = self.client.get(self.detail_url, **auth_headers(self.staff_user))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # =========================================================
    # APPROVE / REJECT (PATCH status) — staff/superuser only
    # =========================================================

    def test_anonymous_cannot_approve(self):
        response = self.client.patch(self.detail_url, {"status": "approved"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_regular_user_cannot_approve(self):
        response = self.client.patch(
            self.detail_url, {"status": "approved"}, format='json', **auth_headers(self.regular_user)
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.pending_testimonial.refresh_from_db()
        self.assertEqual(self.pending_testimonial.status, "pending")

    def test_staff_can_approve_testimonial(self):
        response = self.client.patch(
            self.detail_url, {"status": "approved"}, format='json', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.pending_testimonial.refresh_from_db()
        self.assertEqual(self.pending_testimonial.status, "approved")

    def test_staff_can_reject_testimonial(self):
        response = self.client.patch(
            self.detail_url, {"status": "rejected"}, format='json', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.pending_testimonial.refresh_from_db()
        self.assertEqual(self.pending_testimonial.status, "rejected")

    def test_superuser_can_approve_testimonial(self):
        response = self.client.patch(
            self.detail_url, {"status": "approved"}, format='json', **auth_headers(self.superuser)
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_approved_testimonial_appears_on_public_endpoint_after_approval(self):
        self.client.patch(
            self.detail_url, {"status": "approved"}, format='json', **auth_headers(self.staff_user)
        )
        response = self.client.get(self.public_url)
        names = [t['submitted_by'] for t in response.data]
        self.assertIn("Ngozi Chukwu", names)

    def test_rejected_approved_testimonial_disappears_from_public_endpoint(self):
        # boundary: admin reverses a decision — approved testimonial gets rejected afterward
        detail_url = reverse('testimonial-detail', kwargs={'pk': self.approved_testimonial.pk})
        self.client.patch(
            detail_url, {"status": "rejected"}, format='json', **auth_headers(self.staff_user)
        )
        response = self.client.get(self.public_url)
        names = [t['submitted_by'] for t in response.data]
        self.assertNotIn("Femi Adebayo", names)

    def test_invalid_status_value_returns_400(self):
        response = self.client.patch(
            self.detail_url, {"status": "maybe"}, format='json', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_submitted_at_cannot_be_modified(self):
        original = self.pending_testimonial.submitted_at
        self.client.patch(
            self.detail_url, {"submitted_at": "2020-01-01T00:00:00Z"}, format='json',
            **auth_headers(self.staff_user)
        )
        self.pending_testimonial.refresh_from_db()
        self.assertEqual(self.pending_testimonial.submitted_at, original)

    # =========================================================
    # DELETE — staff/superuser only
    # =========================================================

    def test_anonymous_cannot_delete(self):
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_regular_user_cannot_delete(self):
        response = self.client.delete(self.detail_url, **auth_headers(self.regular_user))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Testimonial.objects.filter(id=self.pending_testimonial.id).exists())

    def test_staff_can_delete_testimonial(self):
        response = self.client.delete(self.detail_url, **auth_headers(self.staff_user))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Testimonial.objects.filter(id=self.pending_testimonial.id).exists())

    def test_superuser_can_delete_testimonial(self):
        response = self.client.delete(self.detail_url, **auth_headers(self.superuser))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_deleted_approved_testimonial_disappears_from_public_endpoint(self):
        detail_url = reverse('testimonial-detail', kwargs={'pk': self.approved_testimonial.pk})
        self.client.delete(detail_url, **auth_headers(self.staff_user))
        response = self.client.get(self.public_url)
        names = [t['submitted_by'] for t in response.data]
        self.assertNotIn("Femi Adebayo", names)

    # =========================================================
    # BOUNDARY / EDGE CASES
    # =========================================================

    def test_deactivated_staff_cannot_manage(self):
        self.staff_user.is_active = False
        self.staff_user.save(update_fields=['is_active'])
        response = self.client.get(self.list_url, **auth_headers(self.staff_user))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_updating_nonexistent_testimonial_returns_404(self):
        bad_url = reverse('testimonial-detail', kwargs={'pk': 999999})
        response = self.client.patch(
            bad_url, {"status": "approved"}, format='json', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_deleting_nonexistent_testimonial_returns_404(self):
        bad_url = reverse('testimonial-detail', kwargs={'pk': 999999})
        response = self.client.delete(bad_url, **auth_headers(self.staff_user))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_multiple_testimonials_same_programme_allowed(self):
        # boundary: no uniqueness constraint — multiple people can submit for the same programme
        payload = {
            "submitted_by": "Another Person",
            "programme": "Internship Placement",  # same as self.pending_testimonial
            "content": "Also a great experience.",
        }
        response = self.client.post(self.list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            Testimonial.objects.filter(programme="Internship Placement").count(), 2
        )