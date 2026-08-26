import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from django.conf import settings


def send_transactional_email(to_email, subject, html_content, reply_to_email=None, reply_to_name=None):
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = settings.BREVO_API_KEY

    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
        sib_api_v3_sdk.ApiClient(configuration)
    )

    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=[{"email": to_email}],
        sender={"email": settings.DEFAULT_FROM_EMAIL, "name": "The Clarridge"},
        subject=subject,
        html_content=html_content,
        reply_to={"email": reply_to_email or settings.DEFAULT_FROM_EMAIL, "name": reply_to_name or "The Clarridge"},
    )

    try:
        api_instance.send_transac_email(send_smtp_email)
        return True
    except ApiException:
        return False