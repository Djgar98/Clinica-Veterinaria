# Clinica Veterinaria Arguello - Proyecto Django

Guia rapida para instalar y correr el sistema en entorno local.

## 1. Requisitos

- Python 3.12 o superior
- PowerShell (Windows)
- `pip` actualizado

## 2. Clonar y entrar al proyecto

```powershell
cd C:\Users\Danny Garcia\OneDrive\Documentos\Monografa\Proyecto\Clinica-Veterinaria
```

## 3. Crear entorno virtual e instalar dependencias

```powershell
python -m venv env
.\env\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```
ojo para activar el env del proyecto es "C:\Users\Danny Garcia\OneDrive\Documentos\Monografa\Proyecto\env\Scripts\Activate.ps1"

## 4. Configurar base de datos

Este proyecto usa SQLite por defecto (ya configurado en `config_veterinaria/settings.py`), asi que no necesitas crear una base MySQL para correrlo localmente.

## 5. Ejecutar migraciones y crear usuario administrador

```powershell
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

## 6. Cargar datos de prueba (opcional)

```powershell
python manage.py loaddata fixtures/staff_and_venta.json
```

## 7. Correr el sistema

### Opcion A: servidor Django (desarrollo general)

```powershell
python manage.py runserver
```

### Opcion B: servidor ASGI con Daphne (recomendado para notificaciones/websocket)

```powershell
.\env\Scripts\python.exe -m daphne -b 127.0.0.1 -p 8000 config_veterinaria.asgi:application
```
Para mi pc es cd "C:\Users\Danny Garcia\OneDrive\Documentos\Monografa\Proyecto\Clinica-Veterinaria"      
>> ..\env\Scripts\python.exe -m daphne -b 0.0.0.0 -p 8000 config_veterinaria.asgi:application

## 8. URLs principales

- Sistema: http://127.0.0.1:8000/
- Login: http://127.0.0.1:8000/accounts/login/
- Admin: http://127.0.0.1:8000/admin/

## 9. Pruebas por roles

Para probar el flujo completo por perfiles (`ADMIN`, `ASISTENTE`, `VETERINARIO`, `INVENTARIO`, `DUENO`), revisa:

- `docs/guia_pruebas_roles.md`
