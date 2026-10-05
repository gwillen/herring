# Development image: Python dependencies are baked in at build time; the source
# tree is bind-mounted at /opt/project by docker-compose.yml.
FROM python:3.14-slim-trixie

COPY --from=ghcr.io/astral-sh/uv:0.12.19 /uv /uvx /bin/

# A user matching the host user that docker-compose.yml runs as.
ARG HERRING_UID=1000
ARG HERRING_GID=1000
RUN groupadd -g "$HERRING_GID" herring && useradd -m -u "$HERRING_UID" -g "$HERRING_GID" herring

# The venv lives outside /opt/project, so the bind mount doesn't hide it.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy \
    PATH=/opt/venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /opt/project
COPY pyproject.toml uv.lock .python-version ./
# --no-build: every dependency must come as a prebuilt wheel (there's no
# compiler in this image anyway).
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --no-build

CMD ["./docker-project-command.sh"]
