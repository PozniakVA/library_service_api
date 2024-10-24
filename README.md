# Library Service API

## Starting Celery Worker

To start Celery worker, use the command:

```bash
celery -A library_service_api worker --pool=solo --loglevel=info
```

## Start the celery beat service

```bash
celery -A library_service_api beat --loglevel=info
```

## Launch of Telegram Bot
To start the Telegram bot, set the PYTHONPATH environment variable and execute the startup file:

```
set PYTHONPATH=your_path

python bot_launch.py
```

## Test webhook
If you want to test the webhook locally,
you need to use ngrok. Ngrok allows you 
to expose your local server via a public URL
```
https://ngrok.com/docs/getting-started/#step-1-install
```
