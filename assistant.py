import base64
import os
import time
from collections.abc import Iterator

import groq
import openai
from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

import tools as tool_lib

load_dotenv()

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
# Groq ka vision model (images ke liye). Agar ye model band ho jaye to .env mein badal lein.
GROQ_VISION_MODEL = os.getenv(
    "GROQ_VISION_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct"
)

# OpenAI-compatible providers. Sirf wahi sidebar mein dikhte hain jin ki API key set ho
# (OPENROUTER_API_KEY, MISTRAL_API_KEY).
OPENAI_COMPAT = {
    "OpenRouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "model": os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free"),
        "vision": False,
    },
    "Mistral": {
        "base_url": "https://api.mistral.ai/v1",
        "model": os.getenv("MISTRAL_MODEL", "mistral-small-latest"),
        "vision": True,
    },
}


def _key_name(provider: str) -> str:
    return f"{provider.upper()}_API_KEY"


PROVIDERS = ["Gemini", "Groq"] + [
    name for name in OPENAI_COMPAT if os.getenv(_key_name(name))
]

SYSTEM_PROMPT = (
    "You are a helpful, friendly assistant. "
    "Reply in the same language the user writes in. "
    "Keep answers clear and simple."
)
MAX_TOKENS = 1000
MAX_RETRIES = 5
RETRY_DELAY_SECONDS = 2
MAX_TOOL_ROUNDS = 3

# Sab providers ke API errors, taake CLI/app ek hi jagah catch kar sake
API_ERRORS = (errors.APIError, groq.APIError, openai.APIError)
_STATUS_ERRORS = (groq.APIStatusError, openai.APIStatusError)

# (image bytes, mime type)
ImageData = tuple[bytes, str]


def model_name(provider: str) -> str:
    if provider == "Gemini":
        return GEMINI_MODEL
    if provider == "Groq":
        return GROQ_MODEL
    return OPENAI_COMPAT[provider]["model"]


def supports_images(provider: str) -> bool:
    if provider in ("Gemini", "Groq"):
        return True
    return OPENAI_COMPAT.get(provider, {}).get("vision", False)


def create_client(provider: str = "Gemini"):
    if provider == "Gemini":
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set in your .env file.")
        return genai.Client(api_key=api_key)

    if provider == "Groq":
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is not set in your .env file.")
        return groq.Groq(api_key=api_key)

    if provider in OPENAI_COMPAT:
        api_key = os.getenv(_key_name(provider))
        if not api_key:
            raise RuntimeError(f"{_key_name(provider)} is not set in your .env file.")
        return openai.OpenAI(
            api_key=api_key, base_url=OPENAI_COMPAT[provider]["base_url"]
        )

    raise RuntimeError(f"Unknown provider: {provider}")


def stream_reply(
    client,
    messages: list[dict[str, str]],
    system_prompt: str,
    provider: str = "Gemini",
    image: ImageData | None = None,
    use_tools: bool = False,
) -> Iterator[str]:
    """Jawab ko tukron mein yield karta hai.

    image: (bytes, mime) jo aakhri user message ke saath jaati hai.
    use_tools: True ho to model calculator / web search call kar sakta hai.
    """
    if provider == "Gemini":
        yield from _stream_gemini(client, messages, system_prompt, image, use_tools)
    else:
        yield from _stream_openai_style(
            client, provider, messages, system_prompt, image, use_tools
        )


# ---------------------------------------------------------------- Gemini
def _stream_gemini(client, messages, system_prompt, image, use_tools) -> Iterator[str]:
    contents = [
        types.Content(
            role="model" if m["role"] == "assistant" else "user",
            parts=[types.Part(text=m["content"])],
        )
        for m in messages
    ]
    if image:
        data, mime = image
        contents[-1].parts.append(types.Part.from_bytes(data=data, mime_type=mime))

    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        max_output_tokens=MAX_TOKENS,
        # Python functions dene par SDK khud tool call chala kar jawab wapas bhejta hai
        tools=tool_lib.TOOLS if use_tools else None,
    )

    for attempt in range(MAX_RETRIES + 1):
        sent_text = False
        try:
            response = client.models.generate_content_stream(
                model=GEMINI_MODEL,
                contents=contents,
                config=config,
            )
            for chunk in response:
                if chunk.text:
                    sent_text = True
                    yield chunk.text
            return
        except errors.APIError as exc:
            if exc.code != 503 or sent_text or attempt == MAX_RETRIES:
                raise
            time.sleep(RETRY_DELAY_SECONDS * (2**attempt))


# ------------------------------------------- Groq / OpenRouter / Mistral
def _with_image(messages: list[dict], image: ImageData) -> list[dict]:
    data, mime = image
    url = f"data:{mime};base64,{base64.b64encode(data).decode()}"
    last = messages[-1]
    new_last = {
        "role": last["role"],
        "content": [
            {"type": "text", "text": last["content"]},
            {"type": "image_url", "image_url": {"url": url}},
        ],
    }
    return [*messages[:-1], new_last]


def _stream_openai_style(
    client, provider, messages, system_prompt, image, use_tools
) -> Iterator[str]:
    full_messages = [{"role": "system", "content": system_prompt}, *messages]
    if image:
        full_messages = _with_image(full_messages, image)

    if provider == "Groq":
        model = GROQ_VISION_MODEL if image else GROQ_MODEL
        extra = {"max_completion_tokens": MAX_TOKENS}
        if not image:
            extra["reasoning_effort"] = "low"  # gpt-oss soch mein token kam kharch kare
    else:
        model = OPENAI_COMPAT[provider]["model"]
        extra = {"max_tokens": MAX_TOKENS}

    for round_number in range(MAX_TOOL_ROUNDS + 1):
        # Aakhri round mein tools band, taake model zaroor jawab de
        tools_spec = tool_lib.TOOL_SPECS if use_tools and round_number < MAX_TOOL_ROUNDS else None
        calls = yield from _openai_round(client, model, full_messages, tools_spec, extra)
        if not calls:
            return

        full_messages.append(
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": c["id"],
                        "type": "function",
                        "function": {"name": c["name"], "arguments": c["arguments"]},
                    }
                    for c in calls
                ],
            }
        )
        for c in calls:
            full_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": c["id"],
                    "content": tool_lib.run_tool(c["name"], c["arguments"]),
                }
            )


def _openai_round(client, model, messages, tools_spec, extra):
    """Ek streaming request. Text yield karta hai, aur tool calls ki list return karta hai."""
    for attempt in range(MAX_RETRIES + 1):
        sent_text = False
        calls: dict[int, dict] = {}
        try:
            kwargs = dict(model=model, messages=messages, stream=True, **extra)
            if tools_spec:
                kwargs["tools"] = tools_spec
            stream = client.chat.completions.create(**kwargs)
            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta.content:
                    sent_text = True
                    yield delta.content
                for tc in delta.tool_calls or []:
                    slot = calls.setdefault(
                        tc.index, {"id": "", "name": "", "arguments": ""}
                    )
                    if tc.id:
                        slot["id"] = tc.id
                    if tc.function:
                        if tc.function.name:
                            slot["name"] = tc.function.name
                        if tc.function.arguments:
                            slot["arguments"] += tc.function.arguments
            return [calls[i] for i in sorted(calls)]
        except _STATUS_ERRORS as exc:
            if (
                exc.status_code not in (429, 503)
                or sent_text
                or calls
                or attempt == MAX_RETRIES
            ):
                raise
            time.sleep(RETRY_DELAY_SECONDS * (2**attempt))