"""Fixed-window rate limits for form actions.

Any form action can be rate limited: before an action is executed the values it
declares (by default the submitting client's address) are counted against a
fixed window. Once a limit is used up the action is skipped for the rest of the
window while the remaining actions of the form still run.

Rate limits are opt-in. Sites configure them per action class in::

    DJANGOCMS_FORM_BUILDER_RATE_LIMITS = {
        "default": {"source": (60, 60 * 60)},
        "SendConfirmationMailAction": {"recipient": (3, 24 * 60 * 60)},
    }

``"default"`` applies to every action, an action class name only to that
action. Each entry maps a quota kind to ``(limit, window in seconds)``; ``None``
switches an action's built-in limit off.

Counters are keyed by a keyed hash of the value, so no IP address or email
address is stored in the database.
"""

import hashlib
import hmac
import logging
from datetime import datetime, timedelta, timezone

from django.conf import settings as django_settings
from django.db import IntegrityError, models, transaction
from django.db.models import F
from django.utils.encoding import force_bytes
from django.utils.translation import gettext_lazy as _

from .settings import RATE_LIMIT_IP_META_KEY, RATE_LIMITS

logger = logging.getLogger(__name__)


class SubmissionQuota(models.Model):
    """Fixed-window counters backing the form action rate limits."""

    class Meta:
        verbose_name = _("Submission quota")
        verbose_name_plural = _("Submission quotas")

    key = models.CharField(max_length=64, primary_key=True)
    count = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField(db_index=True)


def get_rate_limits(action_class):
    """Merge an action's built-in limits with the project's configuration."""
    limits = dict(getattr(action_class, "rate_limits", None) or {})
    limits.update(RATE_LIMITS.get("default", {}))
    limits.update(RATE_LIMITS.get(action_class.__name__, {}))
    return {
        kind: (int(spec[0]), int(spec[1]))
        for kind, spec in limits.items()
        if spec is not None
    }


def client_address(request):
    """The submitting client's address, or an empty string if unavailable."""
    return request.META.get(RATE_LIMIT_IP_META_KEY, "") if request else ""


def quota_key(kind, value, window, now):
    """Return a non-reversible, fixed-window quota key without storing PII."""
    bucket = int(now.timestamp()) // window
    message = force_bytes(f"djangocms-form-builder:{kind}:{bucket}:{value}")
    return hmac.new(
        force_bytes(django_settings.SECRET_KEY), message, hashlib.sha256
    ).hexdigest()


def prune_expired(now):
    """Remove counters whose window has passed."""
    SubmissionQuota.objects.filter(expires_at__lt=now).delete()


def consume_quota(kind, value, limit, window, now):
    """Count one use of ``value``; False if its limit is used up already."""
    key = quota_key(kind, value, window, now)
    next_window = (int(now.timestamp()) // window + 1) * window
    expires_at = datetime.fromtimestamp(next_window, tz=timezone.utc) + timedelta(
        seconds=1
    )

    updated = SubmissionQuota.objects.filter(pk=key, count__lt=limit).update(
        count=F("count") + 1
    )
    if updated:
        return True

    try:
        # The savepoint keeps a concurrent insert from breaking an outer
        # transaction, including Django's TestCase transaction.
        with transaction.atomic():
            SubmissionQuota.objects.create(
                key=key,
                count=1,
                expires_at=expires_at,
            )
        return True
    except IntegrityError:
        # Another request created the bucket between UPDATE and INSERT.
        return bool(
            SubmissionQuota.objects.filter(pk=key, count__lt=limit).update(
                count=F("count") + 1
            )
        )


def check_rate_limits(action, form, request):
    """Consume the quotas of ``action`` for this submission.

    Returns ``False`` if a limit is used up, if a value that should be counted
    is unavailable, or if the counters cannot be read: failing closed matters
    because a database incident must not silently disable the limits.
    """
    action_class = type(action)
    limits = get_rate_limits(action_class)
    if not limits:
        return True

    values = action.get_rate_limit_values(form, request)
    now = datetime.now(tz=timezone.utc)
    try:
        prune_expired(now)
        for kind, (limit, window) in limits.items():
            if kind not in values:
                # The action does not know this kind of value - e.g. a
                # recipient limit configured for an action that sends no mail.
                continue
            value = values[kind]
            if not value:
                logger.warning(
                    "%s skipped: no %s to check its rate limit against",
                    action_class.__name__,
                    kind,
                )
                return False
            if not consume_quota(kind, value, limit, window, now):
                logger.warning(
                    "%s skipped: %s rate limit reached",
                    action_class.__name__,
                    kind,
                )
                return False
    except Exception:
        logger.exception("%s skipped: rate limit check failed", action_class.__name__)
        return False
    return True
