from django.conf import settings
from django.core.mail import send_mail
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .serializers import ContactMessageSerializer


class ContactMessageView(generics.CreateAPIView):
    """Public: submits the contact form, sends an email to the org inbox. No DB storage."""
    serializer_class = ContactMessageSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        send_mail(
            subject=f"[Contact Form] {data['subject']}",
            message=(
                f"From: {data['name']} <{data['email']}>\n\n"
                f"{data['message']}"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.CONTACT_FORM_RECIPIENT],
            reply_to=[data['email']],
        )

        return Response(
            {'message': 'Your message has been sent. We will get back to you soon.'},
            status=status.HTTP_200_OK,
        )