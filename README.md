# Library Service API

## 1) Set up .env
Set your variables in .env.example and rename it to .env

## 2) Start Postgres
```bash
docker-compose up -d
```
```bash
python manage.py makemigrations
```
```bash
python manage.py migrate
```

## 3) Start Redis
```bash
docker run -d -p 6379:6379 redis
```

## 4) Starting Celery Worker

To start Celery worker, use the command:

```bash
celery -A library_service_api worker --pool=solo --loglevel=info
```

## 5) Start the celery beat service

```bash
celery -A library_service_api beat --loglevel=info
```

## 6) Launch of Telegram Bot
To start the Telegram bot, set the PYTHONPATH environment variable and execute the startup file:

```bash
set PYTHONPATH=your_path
```
```bash
python bot_launch.py
```

To receive notifications and reminders, visit your personal page(**api/users/me**) and follow the link to connect with the Telegram bot.

## 7) Start Stripe

1) Create account: https://dashboard.stripe.com/
2) Set your STRIPE_PUBLIC_KEY, STRIPE_SECRET_KEY
3) Create your webhook endpoint in Stripe

# Additional information

## Testing Webhook Locally with Ngrok

To test the webhook locally, **ngrok** can be used to expose your local server via a public URL.

### Prerequisites
Make sure to install **ngrok** by following the steps in [the official guide](https://ngrok.com/docs/getting-started/#step-1-install).

### Setup Instructions

1. **Open Command Prompt as Administrator**
   - Go to **Start**, search for **cmd**, right-click on **Command Prompt**, and select **Run as Administrator**.

2. **Install ngrok**
   - Use Chocolatey to install ngrok by running:
     ```
     choco install ngrok
     ```

3. **Authenticate ngrok**
   - Add your ngrok authentication token (replace `<YOUR-TOKEN>` with your actual token):
     ```
     ngrok config add-authtoken <YOUR-TOKEN>
     ```

4. **Start ngrok**
   - Expose your local server running on port `8000` by using:
     ```
     ngrok http 8000
     ```
   - This command will give you a public URL like `https://e849-285-110-133-10.ngrok-free.app`.

5. **Update Django `ALLOWED_HOSTS`**
   - In your Django settings, add the ngrok URL to `ALLOWED_HOSTS`:
     ```python
     ALLOWED_HOSTS = [
         "e849-285-110-133-10.ngrok-free.app"
     ]
     ```

6. **Configure Stripe Webhook Endpoint**
   - Use the ngrok URL with your webhook path when creating a Stripe endpoint:
     ```
     https://e849-285-110-133-10.ngrok-free.app/api/payments_service/webhook/
     ```

## Delete DB
```bash
docker-compose down
```
```bash
docker volume rm library_service_api_postgres_data
```