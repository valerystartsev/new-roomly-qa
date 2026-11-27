FROM python:3.14-slim
WORKDIR /srv/roomly
COPY app/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY app app
COPY app_tests app_tests
COPY migrations migrations
COPY alembic.ini .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
