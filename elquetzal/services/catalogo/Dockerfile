FROM python:3.13-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYCODE=1 \
    PYTHONUNVUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000
CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]