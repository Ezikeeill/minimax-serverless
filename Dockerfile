FROM runpod/pytorch:2.2.1-py3.10-cuda12.1.1-devel-ubuntu22.04

WORKDIR /root

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Clone ComfyUI and install its base dependencies
RUN git clone https://github.com/comfyanonymous/ComfyUI.git /root/ComfyUI
WORKDIR /root/ComfyUI
RUN pip install --no-cache-dir --upgrade torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
RUN pip install --no-cache-dir -r requirements.txt
RUN echo "def fp16_conv3d(*a, **k): pass; fp16_conv3d_out = fp16_conv3d" > /usr/local/lib/python3.10/dist-packages/comfy_kitchen/backends/eager/conv3d.py
RUN pip install --no-cache-dir runpod

# Set up working directory for the serverless handler
ENV COMFY_DISABLE_CUSTOM_OPS=1
WORKDIR /app

# Copy application files
COPY workflow_api.json /app/workflow_api.json
COPY extra_model_paths.yaml /app/extra_model_paths.yaml
COPY handler.py /app/handler.py

ENV COMFYUI_PATH=/root/ComfyUI
ENV PYTHONUNBUFFERED=1

CMD ["python", "-u", "/app/handler.py"]
