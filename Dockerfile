FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt requirements.txt

RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5010

CMD ["uvicorn", "app:app", "--host=0.0.0.0", "--port=5010", "--reload"]
