# Satworx Deployment

## Local URL

Recommended local start:

```text
Double-click start_satworx.bat
```

Or run the backend with Python:

```powershell
python app.py
```

Then open:

```text
http://127.0.0.1:8000/home
```

Do not open the site with a static-only server such as a plain HTML preview or a server that shows `Cannot GET /contact`. Clean routes like `/contact` need the Python backend in `app.py`.

## Online URL

This project includes `render.yaml` for Render hosting.

1. Push this folder to a GitHub repository.
2. Create a new Render Blueprint from that repository.
3. Render will run `python app.py` with `HOST=0.0.0.0`.
4. Render will create your public website URL.

Clean website routes:

```text
/home
/about
/services
/contact
```

The contact form and Satworx Assistant need the Python backend online. The backend stores form leads and assistant questions in:

```text
data/satworx.db
```

## Email Delivery

To receive every contact form submission in your inbox, set these environment variables on your host:

```text
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=1
SMTP_USERNAME=your-email-address
SMTP_PASSWORD=your-app-password
SMTP_FROM=your-email-address
TO_EMAIL=sailohithsahu@gmail.com
```

The app will still save submissions in the database even if email delivery is not configured yet.

## Custom Domain

To use:

```text
https://satworx.com/home
```

you must own the `satworx.com` domain and connect it to your hosting provider.

On Render:

1. Open your Satworx web service.
2. Go to `Settings` -> `Custom Domains`.
3. Add `satworx.com` and optionally `www.satworx.com`.
4. Render will show DNS records.
5. Add those DNS records in your domain provider account.
6. Wait until SSL becomes active.

After DNS is connected, the same backend routes will work:

```text
https://satworx.com/home
https://satworx.com/about
https://satworx.com/services
https://satworx.com/contact
```

Do not upload private runtime files such as `data/satworx.db`, `__pycache__`, or generated screenshot PNG files. They are ignored by `.gitignore`.
