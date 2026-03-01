

import httpx
from celery import shared_task


from fuel_route_api.email_and_sms.email_service import (
    send_password_reset_email,
    send_verification_email,
)
from fuel_route_api.email_and_sms.sms_service import send_sms


@shared_task(
    name="send_verify_email_notification",
    autoretry_for=(httpx.HTTPError, ConnectionError, RuntimeError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def send_verify_email_notification_tasks(to:str, email:str,otp:str,name: str, token:str):
    
    send_sms.send_otp_sms(to=to,otp=otp, name=name)
    send_verification_email(email=email, otp=otp, token=token)
    return None
@shared_task(
    name="send_password_reset_notification",
    autoretry_for=(httpx.HTTPError, ConnectionError, RuntimeError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def send_password_reset_notification_tasks(to:str, email:str,otp:str,name: str, token:str):

    send_sms.send_otp_sms(to=to,otp=otp, name=name)
    send_password_reset_email(email=email, otp=otp, token=token)
    return None