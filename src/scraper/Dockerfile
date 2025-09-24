FROM python:3.10-slim

WORKDIR /app

# Copy the root-level requirements.txt
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy scraper source
COPY . .

RUN apt-get update && apt-get install -y supervisor

# Copy supervisord config
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
