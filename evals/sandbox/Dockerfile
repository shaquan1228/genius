FROM python:3.12-slim-bookworm
RUN apt-get update -qq && apt-get install -y --no-install-recommends bash ca-certificates curl git ocaml-nox ocaml-findlib libjsonm-ocaml-dev ripgrep && rm -rf /var/lib/apt/lists/*
RUN python -m pip install --no-cache-dir --no-deps 'git+https://github.com/evalplus/evalplus.git@6eb1e199c2e370518e7bf3e8eee6322c2b23c89c' 'numpy==2.5.4' 'psutil==7.2.2'
CMD ["python", "-m", "http.server", "7860"]
