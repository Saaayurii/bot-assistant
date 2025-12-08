FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN python3.12 -m pip install wheel setuptools && \
    python3.12 -m pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host=0.0.0.0", "--port=9000", "--log-level=info", "--reload"]


