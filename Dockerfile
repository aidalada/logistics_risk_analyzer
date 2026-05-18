FROM python:3.13-slim

WORKDIR /code

# Копируем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект целиком
COPY . .