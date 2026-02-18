from celery import shared_task
from django.utils import timezone
from character.models import Character

import random


def death_probability(age):
    """Calculate daily death probability based on age"""
    if age < 60:
        return 0
    return ((age - 60) ** 2) / 10000


@shared_task
def check_character_deaths():
    """Daily check to determine if NPCs die based on age"""
    characters = Character.objects.all()
    death_count = 0

    for character in characters:
        age = timezone.now().date() - character.birth_date
        chance = death_probability(age)

        if random.random() < chance:
            character.die()
            death_count += 1

    print(f"{death_count} people died of old age today.")


# # @shared_task
# def start_character_pregnancies():
#     today = timezone.now().date()
#     for partnership in Partnership.objects.filter(partner_is_pregnant=False):
#         partner1 = partnership.partner1
#         partner2 = partnership.partner2

#         if partner1.gender == "Male" and partner2.gender == "Male": continue

#         time_since_last_birth = today - partnership.last_birth_date.days if partnership.last_birth_date else None
#         partner1_age = partner1.get_age()
#         partner2_age = partner2.get_age()

#         chance_of_pregnancy = 0
#         if time_since_last_birth:
#             if time_since_last_birth > 365:
#                 chance_of_pregnancy += 10
#             if partner1_age > 30 and partner2_age > 30:
#                 chance_of_pregnancy += 5

#         if random.random() < (chance_of_pregnancy / 100):
#             if partner1.gender == "Female":
#                 partner1.start_pregnancy()
#             else: partner2.start_pregnancy()


@shared_task
def check_character_pregnancies():
    today = timezone.now().date()
    for character in Character.objects.filter(is_pregnant=True):
        pregnancy_duration = (today - character.pregnancy_start_date).days

        if pregnancy_duration >= 260:
            # Pick a random day in following week for birth
            birth_day = today + timezone.timedelta(days=random.randint(7, 13))
            # Pick a random time for birthday
            random_hour = random.randint(0, 23)
            random_minute = random.randint(0, 59)
            random_second = random.randint(0, 59)
            character.pregnancy_due_date = timezone.make_aware(
                timezone.datetime.combine(
                    birth_day, timezone.time(random_hour, random_minute, random_second)
                )
            )
            handle_birth.apply_async((character.id), eta=character.pregnancy_due_date)
        if random() < character.get_miscarriage_chance():
            character.handle_miscarriage()


@shared_task
def handle_birth(character_id):
    character = Character.objects.get(id=character_id)
    if character:
        character.handle_childbirth()
