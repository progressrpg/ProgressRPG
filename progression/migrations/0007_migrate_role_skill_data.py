from django.db import migrations


def migrate_role_skill_data(apps, schema_editor):
    Role = apps.get_model("progression", "Role")
    CharacterRole = apps.get_model("progression", "CharacterRole")
    CharacterSkill = apps.get_model("progression", "CharacterSkill")
    CharacterQuest = apps.get_model("progression", "CharacterQuest")
    SkillDefinition = apps.get_model("progression", "SkillDefinition")

    # Role becomes authored/global (no more `character` FK) - dedupe by name,
    # preserve each character's former per-character Role as a CharacterRole
    # link to the canonical row, then drop the now-redundant duplicates.
    canonical_role_by_name = {}
    duplicate_role_ids = []
    for role in Role.objects.order_by("id"):
        canonical = canonical_role_by_name.setdefault(role.name, role)
        if role.character_id:
            CharacterRole.objects.get_or_create(
                character_id=role.character_id, role_id=canonical.id
            )
        if role.id != canonical.id:
            duplicate_role_ids.append(role.id)

    # CharacterSkill stops owning name/description - dedupe by name into a
    # shared SkillDefinition, inheriting the skill's first associated role.
    canonical_skill_definition_by_name = {}
    seen_character_skill_definitions = {}
    for skill in CharacterSkill.objects.order_by("id"):
        skill_definition = canonical_skill_definition_by_name.get(skill.name)
        if skill_definition is None:
            first_role = skill.roles.order_by("id").first()
            role = canonical_role_by_name.get(first_role.name) if first_role else None
            skill_definition = SkillDefinition.objects.create(
                name=skill.name,
                description=skill.description,
                role_id=role.id if role else None,
            )
            canonical_skill_definition_by_name[skill.name] = skill_definition

        pair_key = (skill.character_id, skill_definition.id)
        canonical_skill_id = seen_character_skill_definitions.get(pair_key)
        if canonical_skill_id is None:
            seen_character_skill_definitions[pair_key] = skill.id
            skill.skill_definition_id = skill_definition.id
            skill.save(update_fields=["skill_definition"])
        else:
            # Same character already has a skill mapped to this
            # SkillDefinition (duplicate-named skill in the old data) -
            # repoint its quest records onto the canonical row and drop it.
            CharacterQuest.objects.filter(skill_id=skill.id).update(
                skill_id=canonical_skill_id
            )
            skill.delete()

    Role.objects.filter(id__in=duplicate_role_ids).delete()


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("progression", "0006_role_skill_taxonomy"),
    ]

    operations = [
        migrations.RunPython(migrate_role_skill_data, noop_reverse),
    ]
