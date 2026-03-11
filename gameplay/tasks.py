from celery import shared_task
from django.utils import timezone

from character.models import PlayerCharacterLink
from .models import Quest, XpModifier


@shared_task
def update_quest_availability():
    now = timezone.now()
    quests = Quest.objects.all()
    for quest in quests:
        if quest.start_date and quest.start_date <= now:
            quest.is_active = True

        if quest.end_date and quest.end_date < now:
            quest.is_active = False

        if quest.start_date or quest.end_date:
            quest.save()
    return "Successfully updated quest availability"


@shared_task(bind=True)
def end_online_boost(self, modifier_id: int):
    now = timezone.now()
    mod = XpModifier.objects.select_related("character__behaviour").get(id=modifier_id)

    # Superseded / cancelled
    if mod.task_id != self.request.id:
        return "superseded"
    if mod.ends_at is None or mod.ends_at > now or not mod.is_active:
        return "cancelled"

    # End + side effects
    mod.is_active = False
    mod.task_id = None
    mod.ends_at = now
    mod.save(update_fields=["is_active", "task_id", "ends_at"])

    behaviour = getattr(mod.character, "behaviour", None)
    if behaviour:
        behaviour.interrupt_current_activity()
    return "ended"
