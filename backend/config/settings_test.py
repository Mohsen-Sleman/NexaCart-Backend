"""
Settings used ONLY when running pytest (see pytest.ini: DJANGO_SETTINGS_MODULE).
Never imported by the running app - keeps test-only overrides out of the
real settings.py entirely.
"""
from .settings import *

# Celery tasks (send_otp_email, send_order_confirmation_email, ...) run
# synchronously, in-process, instead of needing a real Redis broker +
# worker running during the test suite. The task body still executes for
# real - this only removes the "goes through Redis" part.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Captured in django.core.mail.outbox instead of actually sent - lets
# tests read the real OTP code out of the email body.
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Django's real password hasher (PBKDF2) is deliberately slow (that's the
# point, for real logins). Tests create dozens of users - MD5 here cuts
# the suite's runtime significantly. Never do this outside tests.
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
