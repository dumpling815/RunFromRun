# Build image by following command.
# docker buildx build --env-file .env -t (your_repository):(tag) --push .
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MPLBACKEND=Agg 


WORKDIR /rfr

# Dependency Layering

COPY pyproject.toml uv.lock ./

# Dependency building
RUN uv sync --locked

COPY . .

CMD ["uv", "run", "-m", "app.rfr_server","--port","8000"]