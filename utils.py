import io
import smtplib
from email.mime.text import MIMEText
from pypdf import PdfReader
from config import EMAIL_ADDRESS, EMAIL_APP_PASSWORD

def send_otp_email(to_email, otp_code):
    msg = MIMEText(f"رمز التحقق الخاص بك هو: {otp_code}\nصالح لمدة 5 دقائق.")
    msg["Subject"] = "رمز تحقق - بوت خدمات الجامعة"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_email
    with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as server:
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
        server.send_message(msg)

def extract_pdf_text(pdf_bytes):
    pdf_file = io.BytesIO(pdf_bytes)
    reader = PdfReader(pdf_file)
    full_text = ""
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            full_text += extracted + "\n"
    return full_text