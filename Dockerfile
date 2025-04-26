FROM python:3.11-slim-bookworm

WORKDIR /app


RUN pip install --no-cache-dir -U poetry

COPY poetry.lock pyproject.toml ./

RUN poetry config virtualenvs.create false \
    && poetry install --no-root --no-interaction --no-ansi --compile --without dev

COPY . ./

CMD ["poetry", "run", "python", "-m", "src"]
