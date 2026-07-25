# Stage 1: Build the React Frontend
FROM node:20 AS frontend-build
WORKDIR /app
COPY frontend/package*.json ./frontend/
RUN cd frontend && (npm ci || npm install)
COPY frontend/ ./frontend/
RUN cd frontend && npm run build

# Stage 2: Build the FastAPI Backend & Combine
FROM python:3.10-slim

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create a non-root user (Required for Hugging Face Spaces and Render)
RUN useradd -m -u 1000 user

# Copy the rest of the application files
COPY --chown=user:user . /app

# Copy the compiled frontend from Stage 1
COPY --from=frontend-build --chown=user:user /app/frontend/dist /app/frontend/dist

# Switch to non-root user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Expose port 7860 (Default for Hugging Face Spaces)
EXPOSE 7860

# Start the application
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "7860"]
