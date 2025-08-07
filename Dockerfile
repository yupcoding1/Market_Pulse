# File: Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Create a non-root user
RUN useradd --create-home appuser
USER appuser

# Copy requirements and install dependencies
COPY --chown=appuser:appuser src/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy the rest of the application code
COPY --chown=appuser:appuser src/ .

# Ensure the script is executable
RUN chmod +x main.py

EXPOSE 8000

# Add the installed packages to the Python path and run the app
CMD ["/home/appuser/.local/bin/uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
