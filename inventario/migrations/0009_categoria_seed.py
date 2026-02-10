from django.db import migrations


def seed_categories(apps, schema_editor):
    Categoria = apps.get_model('inventario', 'Categoria')
    names = {name.strip() for name in ['Medicamentos', 'Vacunas', 'Antiparasitarios', 'Antibi?ticos', 'Analg?sicos y antiinflamatorios', 'Anestesia y sedaci?n', 'Vitaminas y suplementos', 'Dermatolog?a', 'Oft?lmicos', 'Otol?gicos', 'Gastrointestinal', 'Cardiolog?a', 'Endocrinolog?a', 'Urolog?a', 'Reproductivos', 'Inmunol?gicos', 'Material quir?rgico', 'Instrumental', 'Curaci?n y vendajes', 'Higiene y limpieza', 'Alimentos y dietas', 'Snacks y premios', 'Accesorios', 'Collares y correas', 'Juguetes', 'Camas y transportadoras', 'Grooming', 'Diagn?stico', 'Laboratorio']}
    existing = set(Categoria.objects.values_list('name', flat=True))
    to_create = [Categoria(name=n) for n in names if n and n not in existing]
    if to_create:
        Categoria.objects.bulk_create(to_create)


def unseed_categories(apps, schema_editor):
    Categoria = apps.get_model('inventario', 'Categoria')
    names = {name.strip() for name in ['Medicamentos', 'Vacunas', 'Antiparasitarios', 'Antibi?ticos', 'Analg?sicos y antiinflamatorios', 'Anestesia y sedaci?n', 'Vitaminas y suplementos', 'Dermatolog?a', 'Oft?lmicos', 'Otol?gicos', 'Gastrointestinal', 'Cardiolog?a', 'Endocrinolog?a', 'Urolog?a', 'Reproductivos', 'Inmunol?gicos', 'Material quir?rgico', 'Instrumental', 'Curaci?n y vendajes', 'Higiene y limpieza', 'Alimentos y dietas', 'Snacks y premios', 'Accesorios', 'Collares y correas', 'Juguetes', 'Camas y transportadoras', 'Grooming', 'Diagn?stico', 'Laboratorio']}
    Categoria.objects.filter(name__in=names).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('inventario', '0008_venta_items_detalle'),
    ]

    operations = [
        migrations.RunPython(seed_categories, unseed_categories),
    ]
