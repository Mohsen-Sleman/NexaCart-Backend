import secrets
import logging
from datetime import timedelta
from django.contrib.auth.hashers import make_password,check_password
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
import requests
from .models import OTP
from .tasks import send_otp_email as send_otp_email_bg

logger = logging.getLogger(__name__)
MAX_OTP_ATTEMPTS = 5

def generate_otp() :
    return f"{secrets.randbelow(1_000_000):06d}"

def hash_otp(otp) :
    return make_password(otp)

def create_otp(user,purpose) :
    otp = generate_otp()
    OTP.objects.create(user = user,purpose=purpose,otp_hash=hash_otp(otp),expires_at=timezone.now() + timedelta(minutes=5))

    return otp

def send_otp_email(user,otp,purpose) :
    send_otp_email_bg.delay(user.email, otp, purpose)

def verify_otp(otp_obj,entered_otp) :
    if otp_obj.used_at is not None :
        return "used"

    if otp_obj.expires_at <= timezone.now() :
        return "expired"

    if otp_obj.attempts >= MAX_OTP_ATTEMPTS :
        return "max_attempts"

    if not check_password(entered_otp,otp_obj.otp_hash) : 
        otp_obj.attempts += 1
        otp_obj.save(update_fields=['attempts'])
        return "invalid"

    otp_obj.used_at = timezone.now()
    otp_obj.save(update_fields=['used_at'])
    return "success"

def reset_password(user,new_password) :
    user.set_password(new_password)
    user.save(update_fields=['password'])


def verify_google_token(access_token):
    try:
        response = requests.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=5,
        )
    except requests.RequestException as e:
        logger.warning("Google token verification network error: %s", e)
        return None

    if response.status_code != 200:
        logger.warning(
            "Google token verification failed: %s - %s",
            response.status_code, response.text
        )
        return None

    try:
        data = response.json()
    except ValueError as e:
        logger.warning("Google response is not valid JSON: %s", e)
        return None

    if "email" not in data:
        logger.warning("Google response missing email: %s", data)
        return None

    if not data.get("email_verified", False):
        logger.warning("Google email not verified: %s", data.get("email"))
        return None

    return data