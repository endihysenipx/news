FROM python:3.12-slim

ENV PLAYWRIGHT_BROWSERS_PATH=0
WORKDIR /srv/news/backend
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m playwright install --with-deps chromium
COPY backend/app ./app
COPY data /srv/news/data

EXPOSE 8001
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
