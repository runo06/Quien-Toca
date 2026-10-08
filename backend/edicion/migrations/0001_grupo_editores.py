from django.db import migrations


def crear_grupo(apps, schema_editor):
    apps.get_model("auth", "Group").objects.get_or_create(name="Editores")


def borrar_grupo(apps, schema_editor):
    apps.get_model("auth", "Group").objects.filter(name="Editores").delete()


class Migration(migrations.Migration):
    """Crea el grupo "Editores": quien esté en él edita desde la página."""

    dependencies = [("auth", "0012_alter_user_first_name_max_length")]

    operations = [migrations.RunPython(crear_grupo, borrar_grupo)]
