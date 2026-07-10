import json
import os
import re
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

SYSTEM_PROMPT = (
    "You are a Structured Knowledge Compiler for AIVE. "
    "Extract specific, actionable knowledge from academic text. "
    "Never use vague labels like 'Artificial intelligence' or 'Education'. "
    "Return valid JSON only."
)

# V0: two models max. Extractors now; reasoners in Week 3+.
AGENT_MODELS = {
    "extractor": os.getenv("OLLAMA_MODEL_EXTRACTOR", "qwen3:8b"),
    "reasoner": os.getenv("OLLAMA_MODEL_REASONER", "deepseek-r1:8b"),
}


def extract_json(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ValueError(f"No JSON found in response:\n{text}")
        return json.loads(match.group())


def call_ollama(
    prompt: str,
    system: str = SYSTEM_PROMPT,
    agent: str = "extractor",
) -> dict:
    model = AGENT_MODELS.get(agent, AGENT_MODELS["extractor"])
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    # Append /no_think to system prompt to disable qwen3's chain-of-thought mode.
    # This cuts response time from ~90s to ~15s for structured JSON tasks without
    # meaningful quality loss on extraction and enrichment prompts.
    system_with_hint = system + " /no_think"
    payload = json.dumps(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": system_with_hint},
                {"role": "user", "content": prompt},
            ],
            "format": "json",
            "stream": False,
            "options": {"temperature": 0.2},
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{host}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as response:
        body = json.loads(response.read().decode("utf-8"))
    return extract_json(body["message"]["content"])


def call_openai(prompt: str, system: str = SYSTEM_PROMPT) -> dict:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY not set.")

    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    return extract_json(response.choices[0].message.content)


def call_llm(
    prompt: str,
    system: str = SYSTEM_PROMPT,
    agent: str = "extractor",
) -> dict:
    # Used exclusively by the T8 Destruction Test in the AIVE Validation Suite.
    # Setting AIVE_DISABLE_AGENT=<agent_name> causes that agent to return an
    # empty result immediately, simulating its removal for ablation scoring.
    disabled_agent = os.getenv("AIVE_DISABLE_AGENT", "").strip().lower()
    if disabled_agent and agent.lower() == disabled_agent:
        return {}

    provider = os.getenv("LLM_PROVIDER", "ollama").lower()
    if provider == "openai":
        return call_openai(prompt, system)
    return call_ollama(prompt, system, agent=agent)
