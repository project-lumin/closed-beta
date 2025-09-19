FROM python:3.12

RUN apt-get update \
    && apd-get install -y curl \
    && curl -Ls https://astral.sh/uv/install.sh | bash \
    && apt-get purge -y curl \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /bot

COPY . .

RUN uv pip install .

CMD ["python3.12", "main.py"]