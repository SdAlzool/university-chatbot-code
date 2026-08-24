import io
import smtplib
from email.mime.text import MIMEText
from pypdf import PdfReader
from config import EMAIL_ADDRESS, EMAIL_APP_PASSWORD

def send_otp_email(to_email, otp_code):
    sender = (EMAIL_ADDRESS or "").strip()
    password = "".join((EMAIL_APP_PASSWORD or "").split())
    recipient = (to_email or "").strip()
    if not sender or not password or not recipient:
        raise ValueError("Email settings or recipient are missing")
    msg = MIMEText(
        f"رمز التحقق الخاص بك هو: {otp_code}\nصالح لمدة 5 دقائق.",
        _charset="utf-8",
    )
    msg["Subject"] = "رمز تحقق - بوت خدمات الجامعة"
    msg["From"] = sender
    msg["To"] = recipient
    server = smtplib.SMTP("smtp.gmail.com", 587, timeout=20)
    try:
        server.starttls()
        server.login(sender, password)
        server.send_message(msg)
    finally:
        try:
            server.quit()
        except Exception:
            server.close()

def extract_pdf_text(pdf_bytes):
    pdf_file = io.BytesIO(pdf_bytes)
    reader = PdfReader(pdf_file)
    full_text = ""
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            full_text += extracted + "\n"
    return full_text