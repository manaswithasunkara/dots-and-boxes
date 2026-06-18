# modal_app.py
#
# Dots & Boxes: Gemma-4-4B-it vs Qwen3-4B
# Both models served via llama.cpp on Modal GPUs
#
# Setup:
#   pip install modal
#   modal setup
#   modal secret create huggingface-secret HF_TOKEN=hf_xxxxx  # for Gemma 4 (gated)
#   modal run modal_app.py::download_models   ← ONE-TIME: pre-populate volumes
#   modal serve  modal_app.py                 ← local dev with hot-reload
#   modal deploy modal_app.py                 ← live public URL

import modal
import os, json, random

# ─────────────────────────────────────────────────────────────────────────────
#  MODELS
# ─────────────────────────────────────────────────────────────────────────────
GEMMA_REPO  = "bartowski/google_gemma-4-E4B-it-GGUF"
GEMMA_FILE  = "google_gemma-4-E4B-it-Q4_K_M.gguf"

QWEN_REPO   = "Qwen/Qwen3-4B-GGUF"
QWEN_FILE   = "Qwen3-4B-Q4_K_M.gguf"

# T4 has 16GB VRAM — a 4B Q4_K_M model needs ~3GB, fits easily
GPU_TYPE    = "T4"


# ─────────────────────────────────────────────────────────────────────────────
#  IMAGE  —  llama.cpp + Gradio + openai client
# ─────────────────────────────────────────────────────────────────────────────
llama_image = (
    modal.Image.from_registry(
        "nvidia/cuda:12.4.0-devel-ubuntu22.04", add_python="3.12"
    )
    .entrypoint([])
    .apt_install("git", "cmake", "build-essential", "curl", "libcurl4-openssl-dev")
    .run_commands(
        "git clone https://github.com/ggml-org/llama.cpp /llama.cpp",
        "cmake /llama.cpp -B /llama.cpp/build -DGGML_CUDA=ON -DBUILD_SHARED_LIBS=OFF",
        "cmake --build /llama.cpp/build --target llama-server -j$(nproc)",
    )
    .pip_install("huggingface_hub", "hf_transfer", "openai")
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
)

# Lightweight image for Gradio UI — rebuilds in seconds, not minutes
gradio_image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("gradio==6.16.0", "fastapi[standard]", "uvicorn", "modal")
    .add_local_file("game.html", "/assets/game.html")
    .add_local_file("gradio-app.py", "/root/gradio-app.py")
)

app = modal.App("dots-and-boxes-llamacpp")

# Separate volumes so models download independently and cache between deploys
gemma_vol = modal.Volume.from_name("gemma4-4b-weights", create_if_missing=True)
qwen_vol = modal.Volume.from_name("qwen3-4b-weights", create_if_missing=True)


# ─────────────────────────────────────────────────────────────────────────────
#  DOWNLOAD MODELS  —  run once before first deploy:
#    modal run modal_app.py::download_models
# ─────────────────────────────────────────────────────────────────────────────
@app.function(
    image=llama_image,
    volumes={"/gemma": gemma_vol, "/qwen": qwen_vol},
    secrets=[modal.Secret.from_name("huggingface-secret")],
    timeout=3600,
)
def download_models():
    from huggingface_hub import hf_hub_download
    import os

    # Gemma 4 — gated, needs HF token
    gemma_path = f"/gemma/{GEMMA_FILE}"
    if not os.path.exists(gemma_path):
        print("Downloading Gemma 4 4B GGUF...")
        hf_hub_download(
            repo_id=GEMMA_REPO,
            filename=GEMMA_FILE,
            local_dir="/gemma",
            token=os.environ["HF_TOKEN"],
        )
        gemma_vol.commit()
        print("Gemma done!")
    else:
        print(f"Gemma already cached at {gemma_path}")

    # Qwen3 — not gated, no token needed
    qwen_path = f"/qwen/{QWEN_FILE}"
    if not os.path.exists(qwen_path):
        print("Downloading Qwen3 4B GGUF...")
        hf_hub_download(
            repo_id=QWEN_REPO,
            filename=QWEN_FILE,
            local_dir="/qwen",
        )
        qwen_vol.commit()
        print("Qwen done!")
    else:
        print(f"Qwen already cached at {qwen_path}")

    print("All models ready!")


# ─────────────────────────────────────────────────────────────────────────────
#  GEMMA 4 4B  —  llama-server on port 8081
# ─────────────────────────────────────────────────────────────────────────────
@app.cls(
    image=llama_image,
    gpu=GPU_TYPE,
    volumes={"/gemma": gemma_vol},
    min_containers=1,
    timeout=600,
    secrets=[modal.Secret.from_name("huggingface-secret")],  # Gemma 4 is gated
)
class GemmaServer:
    @modal.enter()
    def start(self):
        import subprocess, time
        from huggingface_hub import hf_hub_download

        # Download GGUF if not cached
        model_path = f"/gemma/{GEMMA_FILE}"
        if not os.path.exists(model_path):
            print("Downloading Gemma 4 4B GGUF...")
            hf_hub_download(
                repo_id=GEMMA_REPO,
                filename=GEMMA_FILE,
                local_dir="/gemma",
                token=os.environ["HF_TOKEN"],
            )
            gemma_vol.commit()

        # Launch llama-server as a background subprocess
        # --chat-template gemma  ← REQUIRED for Gemma 4 (different BOS/EOS tokens)
        self.proc = subprocess.Popen([
            "/llama.cpp/build/bin/llama-server",
            "-m", model_path,
            "--chat-template", "gemma",
            "--port", "8081",
            "--host", "0.0.0.0",
            "-ngl", "99",  # offload all layers to GPU
            "-c", "2048",
            "--temp", "0.7",
            "-np", "4",  # 4 parallel slots
        ])
        # Wait for server to be ready
        time.sleep(8)
        print("Gemma server ready on :8081")

    @modal.exit()
    def stop(self):
        self.proc.terminate()

    @modal.method()
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        from openai import OpenAI
        client = OpenAI(base_url="http://localhost:8081/v1", api_key="none")
        resp = client.chat.completions.create(
            model="local",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=100,
            stop=["\n\n"],
        )
        return resp.choices[0].message.content or ""


# ─────────────────────────────────────────────────────────────────────────────
#  QWEN3 4B  —  llama-server on port 8082
# ─────────────────────────────────────────────────────────────────────────────
@app.cls(
    image=llama_image,
    gpu=GPU_TYPE,
    volumes={"/qwen": qwen_vol},
    min_containers=1,
    timeout=600,
    # Qwen3-4B is NOT gated — no HF token needed
)
class QwenServer:
    @modal.enter()
    def start(self):
        import subprocess, time
        from huggingface_hub import hf_hub_download

        model_path = f"/qwen/{QWEN_FILE}"
        if not os.path.exists(model_path):
            print("Downloading Qwen3 4B GGUF...")
            hf_hub_download(
                repo_id=QWEN_REPO,
                filename=QWEN_FILE,
                local_dir="/qwen",
            )
            qwen_vol.commit()

        # --jinja   ← use the embedded Qwen3 chat template (required for /no_think)
        self.proc = subprocess.Popen([
            "/llama.cpp/build/bin/llama-server",
            "-m", model_path,
            "--jinja",
            "--port", "8082",
            "--host", "0.0.0.0",
            "-ngl", "99",
            "-c", "2048",
            "--temp", "0.7",
            "-np", "4",
        ])
        time.sleep(8)
        print("Qwen server ready on :8082")

    @modal.exit()
    def stop(self):
        self.proc.terminate()

    @modal.method()
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        from openai import OpenAI
        client = OpenAI(base_url="http://localhost:8082/v1", api_key="none")
        resp = client.chat.completions.create(
            model="local",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=100,
            stop=["\n\n"],
        )
        return resp.choices[0].message.content or ""


# ─────────────────────────────────────────────────────────────────────────────
#  GRADIO WEB SERVER  —  launches gradio_app.py as a subprocess
# ─────────────────────────────────────────────────────────────────────────────
@app.function(
    image=gradio_image,
    min_containers=1,
    max_containers=1,
    timeout=600,
    scaledown_window=300,
)
@modal.web_server(7860, startup_timeout=120, label="dots-and-boxes")
def serve():
    import subprocess
    subprocess.Popen(["python", "/root/gradio-app.py"])
