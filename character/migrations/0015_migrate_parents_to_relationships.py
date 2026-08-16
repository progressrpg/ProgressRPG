# Hand-written: migrates data out of the old parents M2M into
# CharacterRelationship/CharacterRelationshipMembership rows (type
# parent_child, variant biological - the only kind `parents.add()` ever
# produced) before dropping the field.

from django.db import migrations


def migrate_parents_to_relationships(apps, schema_editor):
    Character = apps.get_model("character", "Character")
    CharacterRelationship = apps.get_model("character", "CharacterRelationship")
    CharacterRelationshipMembership = apps.get_model(
        "character", "CharacterRelationshipMembership"
    )

    for child in Character.objects.prefetch_related("parents").all():
        for parent in child.parents.all():
            relationship = CharacterRelationship.objects.create(
                relationship_type="parent_child", variant="biological"
            )
            CharacterRelationshipMembership.objects.create(
                relationship=relationship, character=parent, role="parent"
            )
            CharacterRelationshipMembership.objects.create(
                relationship=relationship, character=child, role="child"
            )


def noop_reverse(apps, schema_editor):
    # Not attempting to reconstruct the old M2M from CharacterRelationship
    # rows - by the time this would run in reverse, PARENT_CHILD
    # relationships may also include ones never expressible as `parents`
    # (e.g. created directly via the new API).
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("character", "0014_relationship_variant_and_role_choices"),
    ]

    operations = [
        migrations.RunPython(
            migrate_parents_to_relationships, reverse_code=noop_reverse
        ),
        migrations.RemoveField(
            model_name="character",
            name="parents",
        ),
    ]
