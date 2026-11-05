import os
import time
import json
import uuid
import base64
import urllib.request
import urllib.parse
import subprocess
import runpod

COMFYUI_URL = "http://127.0.0.1:8188"
COMFYUI_PATH = os.environ.get("COMFYUI_PATH", "/root/ComfyUI")

def start_comfyui():
    """Start ComfyUI headlessly if it is not already running."""
    try:
        urllib.request.urlopen(f"{COMFYUI_URL}/system_stats", timeout=2)
        return
    except Exception:
        pass

    cmd = [
        "python", f"{COMFYUI_PATH}/main.py",
        "--listen", "127.0.0.1",
        "--port", "8188",
        "--extra-model-paths-config", "/workspace/extra_model_paths.yaml"
    ]
    subprocess.Popen(cmd)

    # Wait for ComfyUI to become responsive
    for _ in range(60):
        try:
            urllib.request.urlopen(f"{COMFYUI_URL}/system_stats", timeout=2)
            return
        except Exception:
            time.sleep(1)
    raise RuntimeError("ComfyUI failed to start within 60 seconds.")

def queue_prompt(prompt_workflow):
    p = {"prompt": prompt_workflow, "client_id": str(uuid.uuid4())}
    data = json.dumps(p).encode('utf-8')
    req = urllib.request.Request(f"{COMFYUI_URL}/prompt", data=data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode('utf-8'))

def get_history(prompt_id):
    with urllib.request.urlopen(f"{COMFYUI_URL}/history/{prompt_id}") as response:
        return json.loads(response.read().decode('utf-8'))

def handler(job):
    job_input = job.get("input", {})

    prompt_text = job_input.get("prompt")
    seed = job_input.get("seed", 757358688076805)
    image_base64 = job_input.get("image_base64")

    # Load workflow template
    with open("workflow_api.json", "r") as f:
        workflow = json.load(f)

    # 1. Update text prompt if provided (Node 105:104)
    if prompt_text and "105:104" in workflow:
        workflow["105:104"]["inputs"]["prompt"] = prompt_text

    # 2. Update seed if provided (Node 105:15)
    if "105:15" in workflow:
        workflow["105:15"]["inputs"]["noise_seed"] = seed

    # 3. Handle input image if supplied (Node 114)
    if image_base64 and "114" in workflow:
        input_filename = f"input_{uuid.uuid4().hex[:8]}.png"
        input_path = os.path.join(COMFYUI_PATH, "input", input_filename)
        os.makedirs(os.path.dirname(input_path), exist_ok=True)
        with open(input_path, "wb") as img_file:
            img_file.write(base64.b64decode(image_base64))
        workflow["114"]["inputs"]["image"] = input_filename

    # Send job to ComfyUI
    queued = queue_prompt(workflow)
    prompt_id = queued.get("prompt_id")
    if not prompt_id:
        return {"error": "Failed to queue workflow", "details": queued}

    # Poll until execution finishes
    while True:
        history = get_history(prompt_id)
        if prompt_id in history:
            break
        time.sleep(1)

    # Locate the output video file (Node 92)
    outputs = history[prompt_id].get("outputs", {})
    save_video_out = outputs.get("92", {}).get("videos", []) or outputs.get("92", {}).get("images", [])

    if not save_video_out:
        return {"error": "No output video detected in history", "history": history[prompt_id]}

    video_info = save_video_out[0]
    subfolder = video_info.get("subfolder", "")
    filename = video_info.get("filename", "")
    out_dir = os.path.join(COMFYUI_PATH, "output", subfolder)
    video_path = os.path.join(out_dir, filename)

    if not os.path.exists(video_path):
        return {"error": f"Output file missing at {video_path}"}

    # Encode video to base64 for API return
    with open(video_path, "rb") as vf:
        video_b64 = base64.b64encode(vf.read()).decode('utf-8')

    return {
        "status": "success",
        "filename": filename,
        "video_base64": video_b64
    }

if __name__ == "__main__":
    start_comfyui()
    runpod.serverless.start({"handler": handler})