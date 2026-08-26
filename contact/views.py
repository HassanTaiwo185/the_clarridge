from common.email import send_transactional_email
from django.conf import settings
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .serializers import ContactMessageSerializer


class ContactMessageView(generics.CreateAPIView):
    serializer_class = ContactMessageSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        html_content = f"""
        <div style="font-family: -apple-system, Arial, sans-serif; max-width: 500px; margin: 0 auto;">
          <div style="background-color: #0a1f44; padding: 20px; border-radius: 8px 8px 0 0;">
            <h2 style="color: #ffffff; margin: 0; font-weight: normal;">New Contact Form Submission</h2>
          </div>
          <div style="background-color: #f8f9fb; padding: 24px; border-radius: 0 0 8px 8px; border: 1px solid #e5e7eb; border-top: none;">
            <p><strong>Name:</strong> {data['name']}</p>
            <p><strong>Email:</strong> {data['email']}</p>
            <p><strong>Subject:</strong> {data['subject']}</p>
            <div style="background-color: #ffffff; padding: 16px; border-radius: 6px; border: 1px solid #e5e7eb; margin-top: 16px;">
              <p style="white-space: pre-wrap;">{data['message']}</p>
            </div>
          </div>
        </div>
        """

        sent = send_transactional_email(
            settings.CONTACT_FORM_RECIPIENT,
            f"[Contact Form] {data['subject']}",
            html_content,
            reply_to_email=data['email'],
            reply_to_name=data['name'],
        )

        if not sent:
            return Response(
                {'error': 'Unable to send your message. Please try again later.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {'message': 'Your message has been sent. We will get back to you soon.'},
            status=status.HTTP_200_OK,
        )