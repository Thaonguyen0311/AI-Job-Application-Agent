FROM python:3.12-slim

# System libraries required by WeasyPrint (PDF rendering).
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangoft2-1.0-0 libcairo2 libgdk-pixbuf-2.0-0 \
    libffi-dev shared-mime-info fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
# Install core deps. google-adk & playwright are optional; if the pinned
# versions are unavailable for your platform, comment them out in requirements.
RUN pip install --no-cache-dir -r requirements.txt || \
    pip install --no-cache-dir \
      fastapi==0.115.5 "uvicorn[standard]==0.32.1" sqlalchemy==2.0.36 \
      pydantic==2.10.3 pydantic-settings==2.6.1 "python-jose[cryptography]==3.3.0" \
      "passlib[bcrypt]==1.7.4" bcrypt==4.0.1 python-multipart==0.0.19 \
      jinja2==3.1.4 weasyprint==63.1 httpx==0.28.1 apscheduler==3.10.4

# To enable LIVE Playwright scraping / auto-apply, uncomment:
# RUN pip install playwright==1.49.1 && playwright install --with-deps chromium

COPY app ./app

EXPOSE 8000
# Seed jobs + demo user on first boot, then start the API.
CMD ["sh", "-c", "python -m app.seed && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
