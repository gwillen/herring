# Two targets:
#   dev  -- for docker-compose.yml: dependencies (including the dev group) are
#           baked in; the source tree is bind-mounted at /opt/project.
#   prod -- for docker-compose.prod.yml: a self-contained image with the code
#           and collected static files, running gunicorn as a non-root user.
FROM python:3.14-slim-trixie AS base

COPY --from=ghcr.io/astral-sh/uv:0.12.19 /uv /uvx /bin/

# The venv lives outside /opt/project, so the dev bind mount doesn't hide it.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy \
    PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1

WORKDIR /opt/project
COPY pyproject.toml uv.lock .python-version ./


FROM base AS dev

# git lets herring/version.py report the bind-mounted checkout's `git describe`.
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

# A user matching the host user that docker-compose.yml runs as.
ARG HERRING_UID=1000
ARG HERRING_GID=1000
RUN groupadd -g "$HERRING_GID" herring && useradd -m -u "$HERRING_UID" -g "$HERRING_GID" herring

ENV PYTHONDONTWRITEBYTECODE=1
# --no-build: every dependency must come as a prebuilt wheel (there's no
# compiler in this image anyway).
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --no-build

CMD ["./docker-project-command.sh"]


FROM base AS prod

RUN --mount=type=cache,target=/root/.cache/uv \
    UV_COMPILE_BYTECODE=1 uv sync --locked --no-build --no-default-groups

COPY herring ./herring
# Settings require a SECRET_KEY to load; collectstatic doesn't use it, so a
# throwaway value (not kept in the image's environment) is fine here.
RUN SECRET_KEY=collectstatic-only python herring/manage.py collectstatic --noinput

# Shown in logs at startup (see herring/herring/version.py); set by
# scripts/prod.sh from git.
ARG HERRING_VERSION=unknown
ENV HERRING_VERSION=$HERRING_VERSION

# gunicorn keeps a control socket under $HOME/.gunicorn.
RUN useradd --system --create-home herring
USER herring

EXPOSE 8000
CMD ["gunicorn", "--pythonpath=herring", "herring.wsgi", "--bind=0.0.0.0:8000", "--log-file", "-"]
