# OCR Pipeline

A scalable, microservices-based Optical Character Recognition (OCR) pipeline.

## Architecture & Workflow

This project is built using a decoupled, service-oriented architecture to ensure scalability and responsiveness. The workflow is as follows:

1. **User Interface**: Users interact with a **Streamlit** frontend to upload documents for OCR processing.
2. **API Gateway**: The frontend sends the document to a **FastAPI** backend via an HTTP request.
3. **Storage**: The API uploads the raw document to **MinIO**, an S3-compatible object storage service.
4. **Task Queuing**: Instead of processing the document synchronously (which would block the API), the API creates an asynchronous task and pushes it to a **Redis** message queue.
5. **Background Processing**: A **Celery Worker** process continuously monitors Redis for new tasks. It picks up the OCR task, downloads the document from MinIO, and performs the heavy OCR processing.
6. **Result Storage**: Once processing is complete, the worker saves the extracted text and metadata back to MinIO and updates the task status.
7. **Retrieval**: The frontend periodically polls the API for the task status. Once complete, it retrieves the results and displays them to the user.

## Tech Stack

- **Frontend**: [Streamlit](https://streamlit.io/)
- **API / Backend**: [FastAPI](https://fastapi.tiangolo.com/)
- **Task Queue / Asynchronous Processing**: [Celery](https://docs.celeryq.dev/)
- **Message Broker**: [Redis](https://redis.io/)
- **Object Storage**: [MinIO](https://min.io/) (S3-compatible)
- **Containerization**: Docker & Docker Compose
- **Orchestration**: Kubernetes (K8s configuration provided in the `k8s/` directory)
