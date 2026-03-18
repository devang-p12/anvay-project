import os
import json
import re
from dotenv import load_dotenv
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, udf, from_json
from pyspark.sql.types import StringType, StructType, StructField, ArrayType

# Load environment variables
load_dotenv()

# Configuration - use Docker-internal service names
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
KAFKA_TOPIC = "raw_strategic_news"
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASSWORD", "Devang@0305")

# 1. Initialize Spark Session
spark = SparkSession.builder \
    .appName("SovereignEnrichment") \
    .config("spark.sql.shuffle.partitions", "2") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

# 2. Schema for GDELT
schema = StructType([
    StructField("source", StringType()),
    StructField("record_id", StringType()),
    StructField("date", StringType()),
    StructField("url", StringType()),
    StructField("source_name", StringType()),
    StructField("themes", ArrayType(StringType())),
    StructField("persons", ArrayType(StringType())),
    StructField("organizations", ArrayType(StringType())),
    StructField("locations", ArrayType(StringType())),
    StructField("tone", StringType()),
    StructField("ingestion_timestamp", StringType())
])

# 3. Lightweight enrichment using rule-based NER extracted from GDELT fields
# The GDELT data already has persons, organizations, locations pre-extracted.
# We stringify them into a clean summary for Neo4j indexing.
def summarize_entities(persons_json, orgs_json, locations_json, themes_json):
    """Combine GDELT-extracted entities into a concise AI insight string."""
    try:
        persons = persons_json or []
        orgs = orgs_json or []
        locs = locations_json or []
        themes = themes_json or []

        parts = []
        if persons:
            parts.append("Persons: " + ", ".join(persons[:5]))
        if orgs:
            parts.append("Orgs: " + ", ".join(orgs[:5]))
        if locs:
            parts.append("Locations: " + ", ".join(locs[:5]))
        if themes:
            parts.append("Themes: " + ", ".join(str(t) for t in themes[:5]))

        return " | ".join(parts) if parts else "No entities"
    except Exception as e:
        return f"Error: {str(e)}"

summarize_udf = udf(summarize_entities, StringType())

# 4. Read from Kafka (streaming)
df = spark \
  .readStream \
  .format("kafka") \
  .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
  .option("subscribe", KAFKA_TOPIC) \
  .option("startingOffsets", "earliest") \
  .option("maxOffsetsPerTrigger", 100) \
  .load()

# 5. Parse and enrich
parsed_df = df.selectExpr("CAST(value AS STRING)") \
    .select(from_json(col("value"), schema).alias("data")) \
    .select("data.*")

enriched_df = parsed_df.withColumn(
    "ai_insight",
    summarize_udf(
        col("persons"),
        col("organizations"),
        col("locations"),
        col("themes")
    )
)

# 6. Write to Neo4j
def write_to_neo4j(batch_df, batch_id):
    count = batch_df.count()
    if count == 0:
        print(f"Batch {batch_id}: 0 rows, skipping.")
        return
    print(f"Batch {batch_id}: Writing {count} rows to Neo4j...")
    batch_df.write \
        .format("org.neo4j.spark.DataSource") \
        .option("url", NEO4J_URI) \
        .option("authentication.type", "basic") \
        .option("authentication.basic.username", NEO4J_USER) \
        .option("authentication.basic.password", NEO4J_PASS) \
        .option("save.mode", "Append") \
        .option("labels", ":StrategicReport") \
        .mode("Append") \
        .save()
    print(f"Batch {batch_id}: Done writing {count} rows to Neo4j.")

print("Starting Spark streaming enrichment pipeline...")

query = enriched_df.writeStream \
    .foreachBatch(write_to_neo4j) \
    .option("checkpointLocation", "/tmp/checkpoints/strategic_enrichment") \
    .trigger(processingTime="30 seconds") \
    .start()

query.awaitTermination()
