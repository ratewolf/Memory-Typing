FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    QT_QPA_PLATFORM=offscreen

WORKDIR /app

RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
        git \
        libdbus-1-3 \
        libegl1 \
        libfontconfig1 \
        libfreetype6 \
        libgl1 \
        libglib2.0-0t64 \
        libxkbcommon0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY pyproject.toml README.md ./
COPY src ./src
COPY tests ./tests
COPY docs ./docs
RUN pip install --no-cache-dir --no-deps -e .

CMD ["memory-typing"]
