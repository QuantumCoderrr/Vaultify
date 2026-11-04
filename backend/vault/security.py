"""Vault health analysis (weak / reused / stale secrets)."""

from collections import Counter

from django.conf import settings

STALE_AFTER_DAYS = getattr(settings, "VAULT_STALE_AFTER_DAYS", 180)


def analyze(items) -> dict:
    items = list(items)
    with_secret = [i for i in items if i.secret_fingerprint]
    counts = Counter(i.secret_fingerprint for i in with_secret)

    weak = [i for i in with_secret if i.is_weak]
    reused = [i for i in with_secret if counts[i.secret_fingerprint] > 1]
    stale = [i for i in with_secret if i.age_days >= STALE_AFTER_DAYS]

    total = len(with_secret)
    if total:
        flagged = {i.pk for i in weak} | {i.pk for i in reused}
        stale_only = {i.pk for i in stale} - flagged
        penalty = len(flagged) + 0.5 * len(stale_only)
        score = round(100 * max(0.0, 1 - penalty / total))
    else:
        score = 100

    if score >= 85:
        grade, tone = "Excellent", "success"
    elif score >= 65:
        grade, tone = "Good", "info"
    elif score >= 40:
        grade, tone = "Needs work", "warning"
    else:
        grade, tone = "At risk", "danger"

    return {
        "score": score,
        "grade": grade,
        "tone": tone,
        "total": total,
        "weak": weak,
        "reused": reused,
        "stale": stale,
        "strong_count": sum(1 for i in with_secret if (i.strength_score or 0) >= 3),
        "stale_after_days": STALE_AFTER_DAYS,
    }
