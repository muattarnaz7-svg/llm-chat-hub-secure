import streamlit as st

import chat_store
from assistant import (
    API_ERRORS,
    GEMINI_MODEL,
    GROQ_MODEL,
    PROVIDERS,
    SYSTEM_PROMPT,
    create_client,
    stream_reply,
)

st.set_page_config(page_title="LLM Assistant", page_icon="🤖")

st.markdown(
    """
    <style>
    .stApp {
        background:
            radial-gradient(ellipse at 15% 0%, rgba(255, 255, 255, 0.07), transparent 35%),
            radial-gradient(ellipse at 90% 15%, rgba(255, 255, 255, 0.04), transparent 30%),
            linear-gradient(160deg, #000000 0%, #0a0a0a 45%, #1c1c1f 100%);
        background-attachment: fixed;
    }

    [data-testid="stHeader"] { background: rgba(0, 0, 0, 0); }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #000000 0%, #0d0d0f 100%);
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }

    [data-testid="stChatMessage"] {
        margin: 0.65rem 0;
        padding: 0.75rem 1rem;
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 1.25rem;
        background: rgba(20, 20, 22, 0.75);
        box-shadow: 0 0 24px rgba(255, 255, 255, 0.03);
    }

    [data-testid="stChatInput"] {
        border-radius: 1.25rem;
        box-shadow: 0 0 22px rgba(255, 255, 255, 0.08);
    }
    [data-testid="stChatInput"]:focus-within {
        box-shadow: 0 0 28px rgba(255, 255, 255, 0.18);
    }

    /* Grok-style starter chips + sidebar chat buttons */
    .stButton > button {
        border-radius: 999px;
        border: 1px solid rgba(255, 255, 255, 0.16);
        background: rgba(255, 255, 255, 0.04);
        color: #e8e8ea;
        transition: all 0.15s ease;
    }
    .stButton > button:hover {
        border-color: rgba(255, 255, 255, 0.45);
        background: rgba(255, 255, 255, 0.1);
        color: #ffffff;
    }

    .hero { text-align: center; margin: 2.5rem 0 1.5rem; }
    .hero h1 { font-size: 2.4rem; letter-spacing: -0.02em; margin-bottom: 0.2rem; }
    .hero p { color: #9a9aa2; margin: 0; }
    </style>
    """,
    unsafe_allow_html=True,
)

STARTERS = [
    ("💡 Kuch samjhao", "Explain how machine learning works in simple words."),
    ("💻 Code likho", "Write a Python function that checks if a number is prime."),
    ("📅 Din plan karo", "Help me plan a productive study day."),
    ("🗣 Roman Urdu mein", "Mujhe Roman Urdu mein 5 productivity tips do."),
    ("🚀 Project idea", "Give me 5 beginner ML project ideas for my GitHub."),
    ("✍️ Email likho", "Write a short, polite email asking for a deadline extension."),
]

MODEL_NAMES = {"Gemini": GEMINI_MODEL, "Groq": GROQ_MODEL}

# ---------- session state ----------
if "chat_id" not in st.session_state:
    st.session_state.chat_id = chat_store.new_chat_id()
    st.session_state.messages = []


def start_new_chat() -> None:
    st.session_state.chat_id = chat_store.new_chat_id()
    st.session_state.messages = []


def open_chat(chat_id: str) -> None:
    data = chat_store.load_chat(chat_id)
    if data:
        st.session_state.chat_id = chat_id
        st.session_state.messages = data["messages"]


# ---------- sidebar ----------
with st.sidebar:
    st.header("🧠 Model")
    provider = st.selectbox(
        "Kon sa model use karna hai?",
        PROVIDERS,
        key="provider",
        label_visibility="collapsed",
    )
    st.caption(f"{provider} · {MODEL_NAMES[provider]}")

    st.divider()
    st.header("💬 Chats")
    if st.button("➕ New chat", width="stretch", type="primary"):
        start_new_chat()
        st.rerun()

    saved = chat_store.list_chats()
    if not saved:
        st.caption("Abhi koi saved chat nahi hai.")
    for chat in saved:
        is_current = chat["id"] == st.session_state.chat_id
        col_open, col_del = st.columns([5, 1])
        if col_open.button(
            chat["title"],
            key=f"open_{chat['id']}",
            width="stretch",
            disabled=is_current,
        ):
            open_chat(chat["id"])
            st.rerun()
        if col_del.button("🗑", key=f"del_{chat['id']}"):
            chat_store.delete_chat(chat["id"])
            if is_current:
                start_new_chat()
            st.rerun()

    st.divider()
    with st.expander("⚙️ Settings"):
        system_prompt = st.text_area(
            "Assistant personality",
            value=SYSTEM_PROMPT,
            height=120,
        )

# ---------- client ----------
try:
    client = create_client(provider)
except RuntimeError as exc:
    st.error(str(exc))
    st.info(f"`.env` file mai `{provider.upper()}_API_KEY` add karein.")
    st.stop()

# ---------- chat ----------
prompt = st.chat_input("Ask me anything...") or st.session_state.pop(
    "pending_prompt", None
)

if not st.session_state.messages and not prompt:
    st.markdown(
        f"""
        <div class="hero">
            <h1>🤖 LLM Assistant</h1>
            <p>Powered by {provider} · {MODEL_NAMES[provider]}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    cols = st.columns(2)
    for i, (label, text) in enumerate(STARTERS):
        if cols[i % 2].button(label, key=f"starter_{i}", width="stretch"):
            st.session_state.pending_prompt = text
            st.rerun()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt:
    with st.chat_message("user"):
        st.markdown(prompt)

    request_messages = [
        *st.session_state.messages,
        {"role": "user", "content": prompt},
    ]

    with st.chat_message("assistant"):
        try:
            reply = st.write_stream(
                stream_reply(client, request_messages, system_prompt, provider)
            )
        except API_ERRORS as exc:
            code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
            if code in (429, 503):
                st.error(
                    f"{provider} abhi busy hai ya limit khatam ho gayi. "
                    "Thori der baad dobara try karein, ya sidebar se doosra model chunein."
                )
            else:
                st.error(f"{provider} API request failed: {exc}")
        else:
            st.session_state.messages.extend(
                [
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": reply},
                ]
            )
            chat_store.save_chat(
                st.session_state.chat_id, st.session_state.messages
            )
            st.rerun()  # refresh sidebar so the chat title appears