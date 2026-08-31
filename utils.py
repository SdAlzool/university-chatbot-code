import io
import logging
from pypdf import PdfReader
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content

logger = logging.getLogger(__name__)


def send_otp_email(to_email, otp_code):
    from config import SENDGRID_API_KEY, SENDGRID_FROM_EMAIL

    api_key = (SENDGRID_API_KEY or "").strip()
    from_email = (SENDGRID_FROM_EMAIL or "").strip()
    recipient = (to_email or "").strip()

    if not api_key or not from_email or not recipient:
        raise ValueError(
            f"SendGrid settings missing: "
            f"api_key={'SET' if api_key else 'EMPTY'}, "
            f"from={'SET' if from_email else 'EMPTY'}, "
            f"to={'SET' if recipient else 'EMPTY'}"
        )

    subject = "رمز تحقق - بوت خدمات الجامعة"
    html_content = (
        f"<p>رمز التحقق الخاص بك هو: <strong>{otp_code}</strong></p>"
        f"<p>صالح لمدة 5 دقائق.</p>"
    )

    message = Mail(
        from_email=Email(from_email),
        to_emails=To(recipient),
        subject=subject,
        html_content=Content("text/html", html_content),
    )

    client = SendGridAPIClient(api_key)
    response = client.send(message)
    logger.info("SendGrid OTP sent to %s (status=%s)", recipient, response.status_code)

    if response.status_code >= 400:
        raise Exception(f"SendGrid API error {response.status_code}: {response.body}")

    return response

def extract_pdf_text(pdf_bytes):
    pdf_file = io.BytesIO(pdf_bytes)
    reader = PdfReader(pdf_file)
    full_text = ""
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            full_text += extracted + "\n"
    return full_text