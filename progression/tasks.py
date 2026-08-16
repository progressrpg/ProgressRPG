# progression/tasks.py
from datetime import timedelta

from celery import shared_task
from django.db import transaction
from django.db.models import F
from django.db.models.functions import TruncMonth
from django.utils import timezone

from .models import CharacterActivity, CharacterActivityArchive


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def compact_character_activities(self) -> dict:
    """
    Roll completed CharacterActivity rows older than
    GameSettings.activity_compaction_cutoff_days into monthly
    CharacterActivityArchive summaries, then delete the originals.

    Safe to re-run/retry: each (character, activity_definition, month) group
    is archived and deleted in its own transaction, and archive totals are
    incremented rather than overwritten, so a group that's already been
    processed (by this run or a prior one) is simply a no-op the next time
    it's seen.
    """
    from core.models import GameSettings

    cutoff = timezone.now() - timedelta(
        days=GameSettings.current().activity_compaction_cutoff_days
    )

    groups = (
        CharacterActivity.objects.filter(is_complete=True, completed_at__lt=cutoff)
        .annotate(
            month=TruncMonth("completed_at", tzinfo=timezone.get_current_timezone())
        )
        .values("character_id", "activity_definition_id", "month")
        .order_by()
        .distinct()
    )

    archived_groups = 0
    archived_rows = 0

    for group in groups.iterator(chunk_size=100):
        rows_archived = _archive_group(
            character_id=group["character_id"],
            activity_definition_id=group["activity_definition_id"],
            month=group["month"].date(),
            cutoff=cutoff,
        )
        if rows_archived:
            archived_groups += 1
            archived_rows += rows_archived

    return {
        "cutoff": cutoff.isoformat(),
        "archived_groups": archived_groups,
        "archived_rows": archived_rows,
    }


@transaction.atomic
def _archive_group(character_id, activity_definition_id, month, cutoff) -> int:
    """
    Archive and delete one (character, activity_definition, month) group.
    Locks and materializes the matching rows first (rather than
    `.aggregate()` on a `select_for_update()` queryset, which Postgres
    rejects) so the duration/count totals are computed from a consistent,
    locked snapshot immune to a concurrent run processing the same group.
    """
    locked_rows = list(
        CharacterActivity.objects.select_for_update()
        .filter(
            character_id=character_id,
            activity_definition_id=activity_definition_id,
            is_complete=True,
            completed_at__lt=cutoff,
            completed_at__year=month.year,
            completed_at__month=month.month,
        )
        .values_list("id", "duration")
    )
    if not locked_rows:
        # Already archived by a concurrent/earlier run of this task.
        return 0

    total_duration = sum(duration for _id, duration in locked_rows)
    record_count = len(locked_rows)
    row_ids = [row_id for row_id, _duration in locked_rows]

    archive, created = CharacterActivityArchive.objects.get_or_create(
        character_id=character_id,
        activity_definition_id=activity_definition_id,
        month=month,
        defaults={"total_duration": total_duration, "record_count": record_count},
    )
    if not created:
        CharacterActivityArchive.objects.filter(pk=archive.pk).update(
            total_duration=F("total_duration") + total_duration,
            record_count=F("record_count") + record_count,
        )

    CharacterActivity.objects.filter(id__in=row_ids).delete()
    return record_count
