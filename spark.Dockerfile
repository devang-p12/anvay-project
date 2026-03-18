FROM apache/spark:3.5.0

USER root

# Create spark user home directory and give permissions
RUN mkdir -p /home/spark/.ivy2/cache && \
    mkdir -p /home/spark/.ivy2/jars && \
    chown -R spark:spark /home/spark

# Install Python dependencies
RUN pip install --no-cache-dir \
    transformers \
    torch \
    accelerate \
    python-dotenv \
    neo4j

# Set the working directory
WORKDIR /opt/spark/work-dir

USER spark
