FROM python:3.13-slim

WORKDIR /app

# System deps: none needed beyond what pip installs — we use PyMySQL (pure
# Python, no MySQL client headers required) and prebuilt wheels exist for
# cryptography/bcrypt on standard Linux x86_64 for this Python version.

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# No --reload in production. Single worker is intentional, not an
# oversight — see README's Deployment section: market_cache and the
# alert/order schedulers are in-process state that would fragment across
# multiple worker processes.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
