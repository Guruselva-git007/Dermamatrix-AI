FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
# Railway has no GPU. Install the matching CPU-only PyTorch wheels first so the
# resolver does not pull the multi-gigabyte CUDA distribution from PyPI.
RUN python -m pip install --upgrade pip \
    && python -m pip install --index-url https://download.pytorch.org/whl/cpu torch==2.14.0 torchvision==0.29.0 \
    && python -m pip install -r backend/requirements.txt

# The existing project deliberately keeps the optional research model outside
# Git.  Pin and verify the documented upstream research artifact in the image
# so a public deployment has the same model boundary as the verified local app.
# Keep this before application source copies so ordinary code changes reuse the
# verified model layer instead of downloading the artifact again.
RUN mkdir -p backend/models && python -c "from urllib.request import urlretrieve; urlretrieve('https://github.com/ptschandl/dermatoscopy_resnet34_nmed_2020/raw/main/model_last_epoch_34_torchvision0_3_state.ptw', 'backend/models/ham10000_resnet34_research.ptw')" \
    && echo 'a800e9df6330d377ed4a37b32e2cbd78821da5e9c3980a30bd42155d097f0250  backend/models/ham10000_resnet34_research.ptw' | sha256sum -c -

COPY backend backend
COPY frontend frontend

EXPOSE 8080

CMD ["sh", "-c", "gunicorn --chdir backend --bind 0.0.0.0:${PORT:-8080} --workers ${WEB_CONCURRENCY:-1} --timeout 120 app:app"]
