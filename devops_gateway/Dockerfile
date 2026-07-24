FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && groupadd --gid 10001 gateway \
    && useradd --uid 10001 --gid gateway --no-create-home --home-dir /app --shell /usr/sbin/nologin gateway

COPY --chown=gateway:gateway gateway ./gateway

USER gateway

CMD ["python", "-m", "gateway"]
