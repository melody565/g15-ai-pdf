FROM python:3.13-alpine
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py evaluator.py test_evaluator.py ./
CMD ["python","server.py"]
