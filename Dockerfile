FROM python:3.12-slim

RUN pip install uv

WORKDIR /app

COPY . .

CMD ["uv", "run", "python", "-OO", "main.py"]
