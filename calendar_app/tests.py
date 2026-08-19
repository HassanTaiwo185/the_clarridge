from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from .models import CalendarEvent


def auth_headers(user):
    token = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {token.access_token}"}


class CalendarEventPermissionTests(APITestCase):
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

        self.event = CalendarEvent.objects.create(
            title="Student Spotlight",
            description="Monthly feature on a standout student.",
            week_label="Week 1",
            start_date="2026-08-01",
            end_date="2026-08-07",
        )

        self.list_url = reverse('calendar-event-list-create')
        self.detail_url = reverse('calendar-event-detail', kwargs={'pk': self.event.pk})

        self.valid_payload = {
            "title": "Opportunities Bulletin",
            "description": "Roundup of new opportunities.",
            "week_label": "Week 3",
            "start_date": "2026-08-15",
            "end_date": "2026-08-21",
        }

    # =========================================================
    # READ (GET) — AllowAny, regardless of auth state
    # =========================================================

    def test_anonymous_can_list_events(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_anonymous_can_view_single_event(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_regular_user_can_view_event(self):
        response = self.client.get(self.detail_url, **auth_headers(self.regular_user))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_returns_expected_fields(self):
        response = self.client.get(self.detail_url)
        for field in ['id', 'title', 'description', 'week_label', 'start_date', 'end_date']:
            self.assertIn(field, response.data)

    # =========================================================
    # CREATE (POST) — only staff or superuser
    # =========================================================

    def test_anonymous_cannot_create_event(self):
        response = self.client.post(self.list_url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_regular_authenticated_user_cannot_create_event(self):
        response = self.client.post(
            self.list_url, self.valid_payload, format='json', **auth_headers(self.regular_user)
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_user_can_create_event(self):
        response = self.client.post(
            self.list_url, self.valid_payload, format='json', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_superuser_can_create_event(self):
        response = self.client.post(
            self.list_url, self.valid_payload, format='json', **auth_headers(self.superuser)
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_without_title_returns_400(self):
        payload = {**self.valid_payload}
        del payload["title"]
        response = self.client.post(
            self.list_url, payload, format='json', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("title", response.data)

    def test_create_without_week_label_returns_400(self):
        payload = {**self.valid_payload}
        del payload["week_label"]
        response = self.client.post(
            self.list_url, payload, format='json', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("week_label", response.data)

    def test_create_without_dates_returns_400(self):
        payload = {"title": "No Dates", "week_label": "Week 2"}
        response = self.client.post(
            self.list_url, payload, format='json', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("start_date", response.data)
        self.assertIn("end_date", response.data)

    def test_create_with_end_date_before_start_date_returns_400(self):
        payload = {
            "title": "Backwards Event",
            "week_label": "Week 4",
            "start_date": "2026-08-28",
            "end_date": "2026-08-20",
        }
        response = self.client.post(
            self.list_url, payload, format='json', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("end_date", response.data)

    def test_create_with_end_date_equal_to_start_date_is_allowed(self):
        # boundary: single-day event
        payload = {
            "title": "One Day Event",
            "week_label": "Week 2",
            "start_date": "2026-08-10",
            "end_date": "2026-08-10",
        }
        response = self.client.post(
            self.list_url, payload, format='json', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_description_is_optional(self):
        payload = {
            "title": "No Description Event",
            "week_label": "Week 4",
            "start_date": "2026-08-25",
            "end_date": "2026-08-28",
        }
        response = self.client.post(
            self.list_url, payload, format='json', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['description'], '')

    def test_invalid_date_format_returns_400(self):
        payload = {**self.valid_payload, "start_date": "not-a-date"}
        response = self.client.post(
            self.list_url, payload, format='json', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("start_date", response.data)

    def test_empty_title_returns_400(self):
        payload = {**self.valid_payload, "title": ""}
        response = self.client.post(
            self.list_url, payload, format='json', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_events_spanning_multiple_weeks_allowed(self):
        # boundary: "Weeks 1-2" style multi-week ranges must work fine
        payload = {
            "title": "Fellowship Applications Open",
            "week_label": "Weeks 1-2",
            "start_date": "2026-08-01",
            "end_date": "2026-08-14",
        }
        response = self.client.post(
            self.list_url, payload, format='json', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    # =========================================================
    # UPDATE (PATCH) — only staff or superuser
    # =========================================================

    def test_anonymous_cannot_update_event(self):
        response = self.client.patch(self.detail_url, {"title": "Hacked"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_regular_user_cannot_update_event(self):
        response = self.client.patch(
            self.detail_url, {"title": "Hacked"}, format='json', **auth_headers(self.regular_user)
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.event.refresh_from_db()
        self.assertEqual(self.event.title, "Student Spotlight")

    def test_staff_user_can_update_event(self):
        response = self.client.patch(
            self.detail_url, {"title": "Updated Spotlight"}, format='json', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.event.refresh_from_db()
        self.assertEqual(self.event.title, "Updated Spotlight")

    def test_superuser_can_update_event(self):
        response = self.client.patch(
            self.detail_url, {"week_label": "Week 2"}, format='json', **auth_headers(self.superuser)
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.event.refresh_from_db()
        self.assertEqual(self.event.week_label, "Week 2")

    def test_update_with_end_date_before_start_date_returns_400(self):
        response = self.client.patch(
            self.detail_url,
            {"end_date": "2026-07-01"},  # before existing start_date of 2026-08-01
            format='json', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_partial_update_only_title_does_not_require_other_fields(self):
        response = self.client.patch(
            self.detail_url, {"title": "Just Renamed"}, format='json', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # =========================================================
    # DELETE — only staff or superuser
    # =========================================================

    def test_anonymous_cannot_delete_event(self):
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_regular_user_cannot_delete_event(self):
        response = self.client.delete(self.detail_url, **auth_headers(self.regular_user))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(CalendarEvent.objects.filter(id=self.event.id).exists())

    def test_staff_user_can_delete_event(self):
        response = self.client.delete(self.detail_url, **auth_headers(self.staff_user))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CalendarEvent.objects.filter(id=self.event.id).exists())

    def test_superuser_can_delete_event(self):
        response = self.client.delete(self.detail_url, **auth_headers(self.superuser))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    # =========================================================
    # BOUNDARY / EDGE CASES
    # =========================================================

    def test_deactivated_staff_user_cannot_write(self):
        self.staff_user.is_active = False
        self.staff_user.save(update_fields=['is_active'])
        response = self.client.patch(
            self.detail_url, {"title": "Should Fail"}, format='json', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_updating_nonexistent_event_returns_404(self):
        bad_url = reverse('calendar-event-detail', kwargs={'pk': 999999})
        response = self.client.patch(
            bad_url, {"title": "Ghost"}, format='json', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_deleting_nonexistent_event_returns_404(self):
        bad_url = reverse('calendar-event-detail', kwargs={'pk': 999999})
        response = self.client.delete(bad_url, **auth_headers(self.staff_user))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_multiple_events_same_week_label_allowed(self):
        # boundary: no uniqueness constraint — two events can share "Week 4" etc.
        payload = {
            "title": "Monthly Education Publication",
            "week_label": "Week 4",
            "start_date": "2026-08-24",
            "end_date": "2026-08-30",
        }
        response = self.client.post(
            self.list_url, payload, format='json', **auth_headers(self.staff_user)
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_events_are_ordered_by_start_date(self):
        CalendarEvent.objects.create(
            title="Earlier Event", week_label="Week 1",
            start_date="2026-07-01", end_date="2026-07-05",
        )
        response = self.client.get(self.list_url)
        titles = [e['title'] for e in response.data]
        self.assertEqual(titles[0], "Earlier Event")  # earliest start_date first

    def test_list_reflects_multiple_events(self):
        CalendarEvent.objects.create(
            title="Second Event", week_label="Week 2",
            start_date="2026-08-08", end_date="2026-08-14",
        )
        response = self.client.get(self.list_url)
        self.assertEqual(len(response.data), 2)