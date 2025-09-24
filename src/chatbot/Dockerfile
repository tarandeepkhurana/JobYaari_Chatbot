FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install uvicorn

COPY . .

CMD ["uvicorn", "src.backend.app:app", "--host", "0.0.0.0", "--port", "5000"]

