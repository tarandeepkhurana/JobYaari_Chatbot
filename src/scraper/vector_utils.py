from sentence_transformers import SentenceTransformer
import chromadb
import logging
import uuid

logging.basicConfig(
    level=logging.INFO,  
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Silence noisy libraries
logging.getLogger("chromadb").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)

logger = logging.getLogger("vector_utils.py")

# Initialize Chroma client (make sure "chroma" is the service name in docker-compose)
client = chromadb.HttpClient(host="chroma", port=8000)

# Embedding model
embedder = SentenceTransformer("src/chatbot/all-MiniLM-L6-v2")

# Create / get collection
collection = client.get_or_create_collection(
    name="jobs_collection",
    metadata={"hnsw:space": "cosine"}  # cosine similarity
)

def clean_metadata(job):
    for key, value in job.items():
        if value is None:
            job[key] = ""  # replace None with empty string
        elif not isinstance(value, (str, int, float, bool, list, dict)):
            job[key] = str(value)  # convert anything else to string
    return job


def update_chroma(jobs: list[dict]):
    """
    Refresh Chroma with latest job postings:
    - Deletes all existing jobs
    - Adds all scraped jobs with embeddings
    """

    logger.info(f"📊 Refreshing Chroma with {len(jobs)} scraped jobs...")

    # Step 1: Clear old data
    try:
        if collection.count() != 0:
            collection.delete(ids=collection.get()['ids'])
            logger.info("🗑️ Cleared old jobs from Chroma.")
    except Exception as e:
        logger.error(f"⚠️ Error while clearing collection: {e}")

    # Step 2: Prepare new jobs
    new_ids, new_docs, new_embeddings, new_metadata = [], [], [], []

    for job in jobs:
        job_id = str(uuid.uuid4())

        job = clean_metadata(job)

        desc = (
            f"{job.get('title','')} at {job.get('organization','')} - "
            f"{job.get('qualification','')} - "
            f"{job.get('experience','')} - "
            f"{job.get('location','')} - "
            f"{job.get('discipline','')}"
        )

        embedding = embedder.encode(desc).tolist()

        new_ids.append(job_id)
        new_docs.append(desc)
        new_embeddings.append(embedding)
        new_metadata.append(job) 

    # Step 3: Insert all jobs
    if new_ids:
        collection.add(
            ids=new_ids,
            documents=new_docs,
            embeddings=new_embeddings,
            metadatas=new_metadata,
        )
        logger.info(f"✅ Inserted {len(new_ids)} jobs into Chroma.")
    else:
        logger.info("ℹ️ No jobs to insert.")

    logger.info(f"📦 Total jobs in Chroma now: {collection.count()}")
    logger.info("🔄 Chroma refresh complete.\n")

if __name__ == "__main__":
    try:
        # print(client.list_collections())
        # dummy_job = {
        #     "title": "Test Engineer",
        #     "organization": "Demo Org",
        #     "posted_date": "2025-09-19",
        #     "qualification": "B.Tech",
        #     "experience": "0-1 years",
        #     "location": "Remote",
        #     "discipline": "Software"
        # }

        # job_id = generate_job_id(dummy_job)
        # desc = f"{dummy_job['title']} at {dummy_job['organization']} - {dummy_job['qualification']} - {dummy_job['experience']} - {dummy_job['location']} - {dummy_job['discipline']}"
        # embedding = embedder.encode(desc).tolist()

        # collection.add(
        #     ids=[job_id],
        #     embeddings=[embedding],
        #     documents=[desc],
        #     metadatas=[dummy_job],
        # )
        job_id = str(uuid.uuid4())
        print(job_id)
        # print("Count after insert:", collection.delete(ids=collection.get()['ids']))
        # print(collection.get())
    except Exception as e:
        print(e)