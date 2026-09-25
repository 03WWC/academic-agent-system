# Base image
FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to PATH
ENV PATH="/root/.local/bin:$PATH"

# Copy Poetry files (README.md 被 pyproject.toml 的 readme 字段引用)
COPY pyproject.toml poetry.lock* README.md /app/

# Configure Poetry
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root

# Copy application code
COPY customer_support_chat /app/customer_support_chat
COPY web_app /app/web_app
COPY academic_policy_documents /app/academic_policy_documents
COPY faq_config.yaml setup_academic_database.py /app/

# Set environment variables
ENV PYTHONPATH="/app"

# 教务多 Agent Web 服务端口，与 README 和 docker-compose 保持一致
EXPOSE 8001

# Default command: 启动 FastAPI 服务
CMD ["uvicorn", "web_app.app.main:app", "--host", "0.0.0.0", "--port", "8001"]
