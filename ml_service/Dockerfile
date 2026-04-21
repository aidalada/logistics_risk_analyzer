FROM python:3.13-slim

WORKDIR /code/ml_service

COPY ml_service/requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY ml_service/main.py .
COPY logistics_delay_model.pkl .
COPY model_columns.pkl .
COPY logistics_damage_model.pkl .
COPY damage_model_columns.pkl .
COPY logistics_cancel_model.pkl .
COPY cancel_model_columns.pkl .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
