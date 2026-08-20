# OCR Pipeline

A scalable, microservices-based Optical Character Recognition (OCR) pipeline.

## Architecture & Workflow

![OCR Pipeline Workflow Chart](./OCR-Pipeline%20workflow%20chart.png)
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

## How to Run the Application

The easiest way to run the entire microservices stack (Frontend, API, Worker, Redis, and MinIO) locally is by using **Docker Compose**. All services are pre-configured to communicate with each other via internal Docker network endpoints.

### Prerequisites
- Install [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/).

### Steps to Run

1. **Clone the repository and navigate to the folder:**
   ```bash
   git clone <your-repository-url>
   cd T_OCR2
   ```

2. **Configure Environment Variables (Optional):**
   The `docker-compose.yml` provides default environment variables that work out of the box. 
   If you wish to change them, copy the `.env.example` file to `.env` and fill in your custom values.
   ```bash
   cp .env.example .env
   ```

3. **Start the Services (Docker Compose):**
   The simplest way to run the stack is directly through Docker Compose. Run the following command in the root directory:
   ```bash
   docker-compose up --build -d
   ```
   *This command will build the frontend, API, and worker images, and spin up all 6 containers in the background.*

4. **Alternative: Smart Startup Script:**
   You can also use the smart startup script to toggle between local Docker deployment and Kubernetes deployment. Ensure you have set your desired environment in your `.env` file:
   - Set `USE_K8S=false` to deploy locally using Docker Compose.
   - Set `USE_K8S=true` to deploy to a Kubernetes cluster using `kubectl`.
   
   Run the following command:
   ```powershell
   .\start.ps1
   ```

4. **Access the Application:**
   Once the containers are running, you can access the different endpoints in your browser:
   - **Streamlit Frontend (UI):** [http://localhost:8501](http://localhost:8501)
   - **FastAPI Documentation (Swagger UI):** [http://localhost:8000/docs](http://localhost:8000/docs)
   - **MinIO Object Storage Console:** [http://localhost:9001](http://localhost:9001) *(Default Login: minioadmin / minioadmin)*

5. **Stop the Services:**
   To stop the application and tear down the containers:
   ```bash
   docker-compose down
   ```

## How the Endpoints Connect

If you decide to run the python applications directly on your host machine without Docker, you will need to start Redis and MinIO manually and define the following environment variables so the Python processes can find them:

- `CELERY_BROKER_URL`: URL to your Redis instance (e.g., `redis://localhost:6379/0`). Used by the **API** and **Worker** to communicate.
- `S3_ENDPOINT_URL`: URL to your MinIO/S3 instance (e.g., `http://localhost:9000`). Used by the **API** and **Worker** to store/retrieve files.
- `AWS_ACCESS_KEY_ID` & `AWS_SECRET_ACCESS_KEY`: Credentials for MinIO.
- `S3_BUCKET_NAME`: Name of the bucket (e.g., `ocr-bucket`).
- `API_URL`: The URL where your FastAPI is running (e.g., `http://localhost:8000/ocr`). Used by the **Frontend** to send requests.
