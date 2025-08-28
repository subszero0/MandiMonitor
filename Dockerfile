FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install wheel
RUN pip install --upgrade pip setuptools wheel

# Copy requirements and paapi5-python-sdk-example for installation
COPY requirements.txt .
COPY paapi5-python-sdk-example ./paapi5-python-sdk-example

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy remaining application code
COPY . .

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "-m", "bot.main"]