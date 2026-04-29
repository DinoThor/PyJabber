FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
RUN groupadd --system --gid 999 nonroot \
 && useradd --system --gid 999 --uid 999 --create-home nonroot
WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_NO_DEV=1
ENV UV_TOOL_BIN_DIR=/usr/local/bin

COPY ./pyjabber /app
RUN chown -R nonroot:nonroot /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-cache

ENV PATH="/app/.venv/bin:$PATH"
USER nonroot

ENTRYPOINT ["python", "pyjabber/__main__.py"]
