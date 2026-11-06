FROM runpod/worker-comfy:latest

# Load volume model paths
COPY extra_model_paths.yaml /comfyui/extra_model_paths.yaml

# Copy workflow definition
COPY workflow_api.json /workflow_api.json

WORKDIR /
