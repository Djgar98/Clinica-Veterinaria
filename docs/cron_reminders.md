# Programación automática de recordatorios

Este proyecto incluye el comando:

```
python manage.py send_cita_reminders
```

Puedes programarlo con **cron** (Linux/Mac) para que se ejecute cada 15 minutos.

Ejemplo de crontab:

```
*/15 * * * * cd /ruta/al/proyecto && /ruta/a/python manage.py send_cita_reminders >> logs/reminders.log 2>&1
```

En Windows puedes usar el **Programador de tareas**:
- Acción: iniciar programa
- Programa: `python`
- Argumentos: `manage.py send_cita_reminders`
- Iniciar en: la carpeta del proyecto

### Ajustes en settings.py

```
REMINDER_HOURS_BEFORE = 24
REMINDER_SEND_WINDOW_MINUTES = 30
WHATSAPP_WEBHOOK_URL = ''
WHATSAPP_WEBHOOK_TOKEN = ''
```

Si no configuras WhatsApp, se marcará como omitido.
