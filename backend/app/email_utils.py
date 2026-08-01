"""
Real SMTP email delivery — currently only used for password reset.

Config-driven like every other optional integration in this app (Azure
OpenAI, Azure AI Search, Purview, Postgres, Redis...): if SMTP_HOST/
SMTP_USER/SMTP_PASSWORD aren't set, `send_email` returns False rather
than pretending to have sent anything.
"""

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib

from app import config


def send_email(to_address: str, subject: str, body: str) -> bool:
    """Send a plain-text email over SMTP."""

    if not config.SMTP_CONFIGURED or not to_address:
        print("SMTP NOT CONFIGURED")
        return False

    msg = MIMEMultipart()
    msg["From"] = config.SMTP_FROM or config.SMTP_USER
    msg["To"] = to_address
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        print("=" * 60)
        print("SMTP HOST :", config.SMTP_HOST)
        print("SMTP PORT :", config.SMTP_PORT)
        print("SMTP USER :", config.SMTP_USER)
        print("SMTP FROM :", config.SMTP_FROM)
        print("=" * 60)

        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=20) as server:
            server.set_debuglevel(1)

            server.ehlo()

            server.starttls()

            server.ehlo()

            login_result = server.login(
                config.SMTP_USER,
                config.SMTP_PASSWORD
            )

            print("LOGIN RESULT:", login_result)

            send_result = server.sendmail(
                msg["From"],
                [to_address],
                msg.as_string()
            )

            print("SEND RESULT:", send_result)
            print("NOOP:", server.noop())

        print("EMAIL SENT SUCCESSFULLY")
        return True

    except Exception as e:
        print("=" * 60)
        print("SMTP ERROR")
        print(type(e))
        print(e)
        print("=" * 60)
        return False


def send_otp_email(email: str, otp: str) -> bool:
    subject = "ComplianceAI - Email Verification OTP"

    body = f"""
Hello,

Welcome to ComplianceAI.

Your One-Time Password (OTP) is:

{otp}

This OTP is valid for 10 minutes.

If you did not request this verification, please ignore this email.

Regards,
ComplianceAI Team
"""

    return send_email(email, subject, body)


def send_welcome_email(email: str, username: str, temporary_password: str) -> bool:
    subject = "Welcome to ComplianceAI"

    body = f"""
Hello {username},

Your ComplianceAI account has been created successfully.

Login Email:
{email}

Temporary Password:
{temporary_password}

After your first login you will be asked to:

• Verify your email
• Change your password

Regards,
ComplianceAI Team
"""

    return send_email(email, subject, body)


def send_password_reset_email(email: str, otp: str) -> bool:
    subject = "ComplianceAI Password Reset"

    body = f"""
Hello,

We received a password reset request.

Your OTP is:

{otp}

This OTP expires in 10 minutes.

If you did not request a password reset, ignore this email.

Regards,
ComplianceAI Team
"""

    return send_email(email, subject, body)


def send_password_changed_email(email: str) -> bool:
    subject = "Password Changed Successfully"

    body = """
Hello,

Your ComplianceAI password has been changed successfully.

If you did not perform this action, contact your administrator immediately.

Regards,
ComplianceAI Team
"""

    return send_email(email, subject, body)
