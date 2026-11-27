FROM python:3.12-slim-bookworm AS tools
RUN apt-get update -qq && apt-get install -y --no-install-recommends bash ca-certificates curl git ocaml-nox ocaml-findlib libjsonm-ocaml-dev ripgrep && rm -rf /var/lib/apt/lists/*
RUN python -m pip install --no-cache-dir --no-deps 'git+https://github.com/evalplus/evalplus.git@6eb1e199c2e370518e7bf3e8eee6322c2b23c89c' 'numpy==2.5.4' 'psutil==7.2.2'
RUN curl -fsSL https://github.com/bendlang/bend/releases/download/v2.0.40/bend-2.0.40-linux-x64.tar.gz -o /tmp/bend.tar.gz \
    && echo 'c9ff8d67bd903fb6ad9a26b43d8a62c01021de82a44d55ce4a3dcd4732113d6b  /tmp/bend.tar.gz' | sha256sum --check \
    && tar -xzf /tmp/bend.tar.gz -C /opt && rm /tmp/bend.tar.gz
ENV PATH="/opt/bend/bin:${PATH}"
FROM tools AS local
RUN useradd --uid 10001 --create-home evaluator
USER 10001:10001
WORKDIR /home/evaluator
CMD ["tail", "-f", "/dev/null"]

FROM tools AS hosted
CMD ["python", "-m", "http.server", "7860"]
