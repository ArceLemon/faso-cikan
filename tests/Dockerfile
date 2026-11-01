FROM python:3.12-slim
RUN pip install --no-cache-dir pytest==8.3.4 httpx==0.28.1
WORKDIR /tests
ENTRYPOINT ["python", "-m", "pytest", "-p", "no:cacheprovider", "-v", "/tests"]
