
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from fuel_route_api.breaker.email_breaker import email_breaker as breaker
from fuel_route_api.core.env import (
    EMAIL_PASSWORD,
    EMAIL_PORT,
    EMAIL_SERVER,
    EMAIL_USE_TLS,
    EMAIL_USER,
    FRONTEND_URL,
)


def sync_send(message: MIMEMultipart):
    if not EMAIL_USER or not EMAIL_PASSWORD:
        raise ValueError("EMAIL_USER and EMAIL_PASSWORD must be configured")
    def smtp_operation():
        with smtplib.SMTP(
            host=EMAIL_SERVER,
            port=EMAIL_PORT,
            timeout=5,
        ) as server:
            if EMAIL_USE_TLS:
                server.starttls()

            server.login(
                EMAIL_USER,
                EMAIL_PASSWORD,
            )

            server.send_message(message)

    return breaker.sync_call(smtp_operation)


async def async_send(message):

    if not EMAIL_USER or not EMAIL_PASSWORD:
        raise ValueError("EMAIL_USER and EMAIL_PASSWORD must be configured")
    
    async def smtp_operation():
        await aiosmtplib.send(
            message,
            hostname=EMAIL_SERVER,
            port=EMAIL_PORT,
            username=EMAIL_USER,
            password=EMAIL_PASSWORD,
            start_tls=EMAIL_USE_TLS,
        )

    try:
        return await breaker.call(smtp_operation)
    except Exception as e:
        print(f"Error sending email: {e}")
        raise


def send_verification_email(email: str, otp: str, token: str):
    if not EMAIL_USER or not EMAIL_PASSWORD:
        raise ValueError("EMAIL_USER and EMAIL_PASSWORD must be configured")
    
    verify_link = f"{FRONTEND_URL}/verify-email.html?token={token}"

    html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6;">
            <h2>Verify Your Email</h2>
            <p>Hello,</p>
            <p>Your one-time password (OTP) is:</p>
            <h3 style="color:#007bff;">{otp}</h3>
            <p>You can also verify your email by clicking the link below:</p>
            <a href="{verify_link}" style="display:inline-block;background:#28a745;color:white;padding:10px 20px;
               text-decoration:none;border-radius:4px;">Verify Email</a>
            <p>This link will expire in 1 hour.</p>
            <hr>
            <p>If you did not request this, please ignore this message.</p>
            <p>Best regards,<br>Your Support Team</p>
        </body>
        </html>
        """

    message = MIMEMultipart("alternative")
    message["Subject"] = "Verify Your Email"
    message["From"] = EMAIL_USER
    message["To"] = email
    message.attach(MIMEText(html_content, "html"))

    try:
        sync_send(message=message)
    except Exception as e:
        print(f"Error sending verification email: {e}")
        raise


def send_password_reset_email(email: str, otp: str, token: str):
    reset_link = f"{FRONTEND_URL}/reset-password.html?token={token}"

    html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6;">
            <h2>Password Reset Request</h2>
            <p>Hello,</p>
            <p>Your password reset OTP is:</p>
            <h3 style="color:#dc3545;">{otp}</h3>
            <p>Alternatively, click below to reset your password:</p>
            <a href="{reset_link}" style="display:inline-block;background:#007bff;color:white;padding:10px 20px;
               text-decoration:none;border-radius:4px;">Reset Password</a>
            <p>This link will expire in 1 hour.</p>
            <hr>
            <p>If you didn’t request this, please ignore this email.</p>
            <p>Best regards,<br>Your Support Team</p>
        </body>
        </html>
        """

    message = MIMEMultipart("alternative")
    message["Subject"] = "Reset Your Password"
    message["From"] = EMAIL_USER
    message["To"] = email
    message.attach(MIMEText(html_content, "html"))

    try:
        sync_send(message=message)
    except Exception as e:
        print(f"Error sending password reset email: {e}")
        raise


async def async_send_paid_email(email: str, name: str, amount):
    if not EMAIL_USER or not EMAIL_PASSWORD:
        raise ValueError("EMAIL_USER and EMAIL_PASSWORD must be configured")
    
    html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6;">
            <h2>Subscription Payment Notification</h2>
            <p>Hello {name},</p>
            <p> You have successfully made a payment {amount}</p>
            <p>Best regards,<br>Your Support Team</p>
        </body>
        </html>
        """

    message = MIMEMultipart("alternative")
    message["Subject"] = "Payment Notice"
    message["From"] = EMAIL_USER
    message["To"] = email
    message.attach(MIMEText(html_content, "html"))

    await async_send(message=message)








