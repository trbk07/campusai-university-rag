FROM python:3.12-slim-bookworm@sha256:e697c81897302a4c4333bade000d98038fbb21eb064f8ee1fd42d02ebcd9d337

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 UV_LINK_MODE=copy UV_NO_CACHE=1 \
    PATH="/app/.venv/bin:$PATH" CAMPUSAI_STATE_ROOT=/var/lib/campusai \
    CAMPUSAI_DEVICE=cpu CAMPUSAI_LLM_CONFIG=/app/configs/free_llm.yaml \
    HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 libglib2.0-0 libgl1 \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv==0.11.28
COPY pyproject.toml uv.lock README.md ./
COPY src/campusai ./src/campusai
COPY scripts ./scripts
COPY configs/free_llm.yaml configs/free_multi_project.yaml ./configs/
COPY configs/local/dense-manifest.json configs/local/runtime-assets.json ./configs/local/
RUN python scripts/release/install_cpu_runtime.py \
    && useradd --uid 10001 --create-home campusai \
    && mkdir -p /var/lib/campusai && chown campusai:campusai /var/lib/campusai
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=180s --retries=3 \
    CMD ["/app/.venv/bin/python", "-c", "import json,urllib.request; assert json.load(urllib.request.urlopen('http://127.0.0.1:8000/ready',timeout=4))['status']=='ready'"]
ENTRYPOINT ["/app/.venv/bin/python", "-m", "scripts.operations.container"]
