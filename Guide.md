## Clone the repo

```bash
git clone "http://gitea.guiaidn.ru/arthur_1PO22/bot-service.git"
cd bot-service
```

## Fill in the .env file

```bash
cp .env.example .env
```

#### .env.example
```bash
REDIS_PASSWORD="password"
REDIS_HOST="redis"
REDIS_PORT="6379"
LLM_PATH="/data/name_of_the_model_file.gguf"
LLM_PORT="8000"
LLM_HOST="0.0.0.0"
LLM_TIMEOUT="600"
LLM_RETRIES="1"
LLM_MAX_TOKENS="100"
LOCAL_STORAGE="/app/storage.json" # you can change it if you want to run the backend container on host

HF_REPO_ID="" # Repo ID from https://huggingface.co
HF_REPO_FILE="" # Specify the file name of neural model to use, otherwise download_models.py will try to download a default one
HF_REPO_DIR="" # Name of a local directory that will be used instead of HF_REPO_FILE


#These environment variables are used for hugging_face.hub to download AI models.
#You can ignore these if you already have a neural network file with trained weights.
#HF_ENDPOINT=https://hf-mirror.com 
#HF_HUB_ENABLE_HF_TRANSFER=0 
```

- LLM_PATH is an env variable that points out the path to the AI model file with weights (it's a shared volume data)
- LLM_MAX_TOKENS is an env variable allows to adjust amount of tokens for the LLM
- LOCAL_STORAGE is a path to the storage.json with knowledge base. You can adjust it if you are going to run the app locally
- HF_REPO_FILE and HF_REPO_ID are variables used to fetch .gguf files from hugging_face.hub. llm_initializer will try to fetch them at building if you decide so. If you have a ready-to-use file with weights, then you can just place the file into bot-service/local_llm/models/ and set HF_REPO_FILE as the name of the file you just resited.
- HF_ENDPOINT and HF_HUB_ENABLE_HF_TRANSFER are used to choose the east-europe (or any other) mirror for hugging_face.hub utility (most likely you will also need to use a VPN)

## Download a Model

If you have 'hf' cli tool installed system-wide, you can use it to download models from huggingface_hub into bot-service/local_llm/models.
Otherwise, you should utilize bot-service/local_llm/download_models.py as described below. 

```bash
set -a && source .env && set +a 

cd local_llm
```

Optionally, setup python environment.

```bash
python -m venv venv
. venv/bin/activate
```

You can either install only huggingface_hub or all libraries from requirements.txt depending on your needs. The requirements.txt file has lots of nvidia libraries, which are quite heavy.

```bash
pip install huggingface_hub

or 

pip install -r requirements.txt # will take a while to download
```

Now you can download models with environment variables from .env file. However, you always can use hf cli utility from huggingface_hub instead.

```bash
python download_models.py
```

## Build the docker-compose

You must have docker-compose and buildx plugings beforehand. We currently have two docker-compose.yml files:
- docker-compose.dev.cpu.yml
- docker-compose.dev.gpu.yml

Both are dedicated for development only. Each one of them drives a dedicated Dockerfile for llm service. Keep in mind that cpu option still requires at least 8GB of RAM and a small AWQ quantized model.

> [!NOTE]
> If you are going to use docker-compose.dev.cpu, then you have to install a stable version of vllm source code in /local_llm/vllm_srouce.

```bash
git clone https://github.com/vllm-project/vllm.git --branch v0.11.0 ./local_llm/vllm_source/
```

You can pass on the GID and UID to docker-compose if you are going to run the app locally afterwards. It will enforce docker to utilize your user when creating new files. Recommended to use only for development.

```bash
docker-compose up --build

or 

export UID=$(id -u) export GID=$(id -g) docker-compose up --build
```

## Run tests in docker-compose

To run modular and integration tests you can utilize both CPU and GPU docker-compose setups.

```bash
docker-compose -f docker-compose.dev.cpu.yml exec -e PYTHONPATH=/app backend pytest -v 

or

docker-compose -f docker-compose.dev.gpu.yml exec -e PYTHONPATH=/app backend pytest -v 
```

Additionally, you can run end-to-end tests.

```bash
docker compose -f docker-compose.dev.cpu.yml exec -e PYTHONPATH=/app backend pytest -s tests/end_to_end.py

or 

docker compose -f docker-compose.dev.cpu.yml exec -e PYTHONPATH=/app backend pytest -s tests/end_to_end.py
```
