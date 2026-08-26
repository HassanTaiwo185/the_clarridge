import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from django.conf import settings


def send_transactional_email(to_email, subject, html_content, reply_to_email=None, reply_to_name=None):
    """
    Sends an email via Brevo's HTTP API instead of raw SMTP,
    since SMTP (port 587) is unreliable/blocked on some hosting platforms.
    """
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = settings.BREVO_API_KEY

    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
        sib_api_v3_sdk.ApiClient(configuration)
    )

    email_kwargs = {
        "to": [{"email": to_email}],
        "sender": {"email": settings.DEFAULT_FROM_EMAIL, "name": "The Clarridge"},
        "subject": subject,
        "html_content": html_content,
    }

    if reply_to_email:
        email_kwargs["reply_to"] = {"email": reply_to_email, "name": reply_to_name or ""}

    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(**email_kwargs)

    try:
        api_instance.send_transac_email(send_smtp_email)
        return True
    except ApiException:
        return False