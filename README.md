# Library Service API

## Starting Celery Worker

To start Celery worker, use the command:

```bash
celery -A library_service_api worker --loglevel=info -P gevent
```

## Launch of Telegram Bot
To start the Telegram bot, set the PYTHONPATH environment variable and execute the startup file:

```
set PYTHONPATH=your_path

python bot_launch.py
```
