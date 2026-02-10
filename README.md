# Clínica Veterinaria Argüello — Proyecto Django

Instrucciones mínimas para levantar el proyecto localmente.

1) Crear entorno virtual (PowerShell):

```powershell
python -m venv env
.\env\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

2) Crear la base de datos MySQL (ejecutar en cliente MySQL):

```sql
CREATE DATABASE veterinaria_arguello CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

3) Configurar la contraseña de la DB en `config_veterinaria/settings.py` (campo `PASSWORD`).

4) Ejecutar migraciones y crear superusuario:

```powershell
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

5) Panel admin: http://127.0.0.1:8000/admin/
