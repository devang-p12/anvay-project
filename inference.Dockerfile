FROM ollama/ollama:latest

# Set working directory
WORKDIR /app

# Ensure curl and python are installed for deployment scripts if needed
RUN apt-get update && apt-get install -y python3 python3-pip curl

# Expose Ollama's default port
EXPOSE 11434

# Copy deployment and benchmark scripts
COPY deploy_inference.py /app/
COPY benchmark_inference.py /app/

# We map /root/.ollama to a volume in docker-compose to persist the Sovereign Data
