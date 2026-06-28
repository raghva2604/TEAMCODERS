import os
import smtplib
from email.message import EmailMessage
from email.utils import formataddr

EMAIL_ADDRESS = os.environ.get("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL")


def send_security_alert(subject: str, body: str, attachment_path: str = None) -> tuple[bool, str]:
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD or not ADMIN_EMAIL:
        error = "Missing EMAIL_ADDRESS, EMAIL_PASSWORD, or ADMIN_EMAIL"
        print(f"[EMAIL] {error}")
        return False, error

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = formataddr(("Face Recognition Security System", EMAIL_ADDRESS))
    message["To"] = ADMIN_EMAIL
    message.set_content(body)

    if attachment_path and os.path.exists(attachment_path):
        try:
            with open(attachment_path, "rb") as f:
                file_data = f.read()
                file_name = os.path.basename(attachment_path)
            message.add_attachment(
                file_data,
                maintype="image",
                subtype="jpeg",
                filename=file_name,
            )
        except Exception as e:
            error = f"Failed to attach image {attachment_path}: {e}"
            print(f"[EMAIL] {error}")
            return False, error

    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(message)
        return True, ""
    except Exception as e:
        error = f"Failed to send alert: {e}"
        print(f"[EMAIL] {error}")
        return False, error
