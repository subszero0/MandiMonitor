FROM python:3.12-slim
COPY . /app
WORKDIR /app
CMD ["python", "-m", "bot.main"] 