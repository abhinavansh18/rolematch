"""Celery tasks for email and push notifications."""
import logging

from celery_app import celery

logger = logging.getLogger(__name__)


@celery.task(bind=True, max_retries=3, default_retry_delay=60)
def send_match_complete_email(self, user_id: str, match_id: str, result_count: int):
    try:
        logger.info(
            "Sending match-complete email: user=%s match=%s results=%d",
            user_id, match_id, result_count,
        )
        # TODO: integrate SendGrid / SES
        # send_email(to=get_user_email(user_id), template="match_complete", ...)
    except Exception as exc:
        raise self.retry(exc=exc)


@celery.task(bind=True, max_retries=3, default_retry_delay=30)
def send_resume_parse_complete(self, user_id: str, resume_id: str, ats_score: int):
    try:
        logger.info(
            "Sending resume-parsed notification: user=%s resume=%s ats=%d",
            user_id, resume_id, ats_score,
        )
    except Exception as exc:
        raise self.retry(exc=exc)
