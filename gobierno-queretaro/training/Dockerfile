FROM nvidia/cuda:12.8.0-devel-ubuntu22.04

# System deps
RUN apt-get update && apt-get install -y \
    python3.12 python3.12-venv python3-pip git curl \
    && rm -rf /var/lib/apt/lists/*

RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1

WORKDIR /app

# Install Python dependencies
COPY training/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy training code and shared modules
COPY training/ /app/training/
COPY orchestrator/ /app/orchestrator/
COPY shared/ /app/shared/

# Default: run classifier RL training
CMD ["python", "-m", "training.train_classifier_rl"]
