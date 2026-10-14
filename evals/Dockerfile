FROM python:3.12.14-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash ca-certificates curl git ocaml-nox ripgrep && rm -rf /var/lib/apt/lists/*
ENV PYTHONDONTWRITEBYTECODE=1
WORKDIR /eval
