FROM runpod/pytorch:2.4.0-py3.10-cuda12.4.1-devel-ubuntu22.04

WORKDIR /root

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Clone ComfyUI master
RUN git clone --depth 1 https://github.com/comfyanonymous/ComfyUI.git /root/ComfyUI
WORKDIR /root/ComfyUI

# Let the base image manage PyTorch/CUDA; install requirements and runpod
RUN pip install --no-cache-dir -r requirements.txt runpod

# In-build smoke test: Catch broken imports in GitHub Actions rather than on RunPod
RUN python -c "import comfy.quant_ops; print('--> ComfyUI quant_ops import OK')"

# Set up working directory for the serverless handler
WORKDIR /app

# Copy application files
COPY workflow_api.json /app/workflow_api.json
COPY extra_model_paths.yaml /app/extra_model_paths.yaml
COPY handler.py /app/handler.py

ENV COMFYUI_PATH=/root/ComfyUI
ENV PYTHONUNBUFFERED=1

CMD ["python", "-u", "/app/handler.py"]
