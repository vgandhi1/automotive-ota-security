# Factory Provisioning Server — containerized
# Build from project root: docker build -f server/Dockerfile .
# CA vault and server certs are generated at build time. In production, mount CA
# and certs as read-only and provisioning_audit.db as a volume.

FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Generate Root CA, Factory CA, server cert, and bootstrap cert
COPY ca/ ca/
RUN python3 ca/scripts/setup_ca.py

COPY server/ server/

ENV HOST=0.0.0.0
ENV PORT=8443
EXPOSE 8443

# Mount point for audit DB: -v provisioning_audit_data:/app/server
VOLUME ["/app/server"]

CMD ["python3", "-m", "uvicorn", "server.factory_server:app", "--host", "0.0.0.0", "--port", "8443", \
     "--ssl-keyfile", "/app/certs/server/server.key", "--ssl-certfile", "/app/certs/server/server.crt", \
     "--ssl-cert-reqs", "2", "--ssl-ca-certs", "/app/ca/root_ca/ca.crt"]
