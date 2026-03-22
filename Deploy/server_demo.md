# Server Demo Notes

## Install

```bash
python3 -m pip install --upgrade pip
pip3 install -r requirements.txt
pip3 install -e .
```

## Start API

```bash
python3 -m paper_agent serve --host 0.0.0.0 --port 8000
```

## Start Workspace

```bash
python3 -m paper_agent ui --host 0.0.0.0 --port 7860
```

## Run CLI demo

```bash
bash Example/demo_cli.sh
```

## Recommended runtime flags

If Ollama is not deployed on the server yet:

```bash
export PAPER_AGENT_LLM_PROVIDER=none
```
