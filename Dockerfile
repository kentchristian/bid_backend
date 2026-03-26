# Step 1: use a python base image
FROM python:3.12-slim 

# Step 2: environment variables (prevents Python from buffering output)
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Step 3: set the working directory inside the container

WORKDIR /app

# Step 4: Install system dependencies (needed for Postgress and Celery)
RUN apt-get update && apt-get install -y \
    libpq-dev gcc curl \
    && rm -rf /var/lib/apt/lists/*

# Step 5: Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Step 6: Copy your project code into the container
COPY . .

# Step 7: The command to run the app

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]