import os
import sys
from huggingface_hub import hf_hub_download, snapshot_download

repo_id = os.environ.get("HF_REPO_ID")
model_file = os.environ.get("HF_REPO_FILE")
repo_dir = os.environ.get("HF_REPO_DIR")
model_dir = "models"

os.makedirs(model_dir, exist_ok=True)

if repo_id and model_file:
    target_path = os.path.join(model_dir, model_file)
    if os.path.exists(target_path):
        print(f"Model file {model_file} already exists, skipping download.")
    else:
        model_path = hf_hub_download(
            repo_id=repo_id,
            filename=model_file,
            local_dir=model_dir,
        )
        print("Downloaded:", model_path)

elif repo_id and repo_dir:
    target_path = os.path.join(model_dir, repo_dir)
    if os.path.exists(target_path):
        print(f"Repository {repo_dir} already exists, skipping download.")
    else:
        snapshot_path = snapshot_download(
            repo_id=repo_id,
            local_dir=target_path,
        )
        print(f"Downloaded entire repo to {snapshot_path}")

else:
    print("ERROR: Either HF_REPO_FILE or HF_REPO_DIR, and HF_REPO_ID environment variables must be set.", file=sys.stderr)
    sys.exit(1)

