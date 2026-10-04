from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

SUBJECT_BY_PURPOSE = {
    'registration': 'Verify your NexaCart account',
    'password_reset': 'Reset your NexaCart password',
}


@shared_task
def send_otp_email(email, otp_code, purpose):
    """
    Takes plain strings (email/otp_code/purpose), not a User instance:
    Celery serializes task arguments (to JSON here) to put them on the
    Redis queue, so passing primitives is both simpler and avoids shipping
    a half-stale copy of the user object across the broker.
    """
    subject = SUBJECT_BY_PURPOSE.get(purpose, 'Your NexaCart verification code')
    message = (
        f"Your verification code is: {otp_code}\n"
        f"This code expires in 10 minutes.\n\n"
        f"If you didn't request this, you can ignore this email."
    )
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email])


@shared_task
def cleanup_expired_otps():
    """
    Periodic task (see CELERY_BEAT_SCHEDULE in settings.py) - deletes OTP
    rows that expired more than a day ago, so the table doesn't grow
    forever. A day of grace (not deleting the instant they expire) in case
    they're ever useful for abuse/debugging investigation shortly after.
    """
    from .models import OTP 

    cutoff = timezone.now() - timezone.timedelta(days=1)
    deleted_count, _ = OTP.objects.filter(expires_at__lt=cutoff).delete()
    return f"Deleted {deleted_count} expired OTP row(s)."
