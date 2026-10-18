import random

import streamlit as st

import auth
import chat_store
import rag
import voice
from assistant import (
    API_ERRORS,
    PROVIDERS,
    SYSTEM_PROMPT,
    create_client,
    model_name,
    stream_reply,
    supports_images,
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

    /* chat ke avatar icons chhupao */
    [data-testid="stChatMessageAvatarUser"],
    [data-testid="stChatMessageAvatarAssistant"],
    [data-testid="stChatMessageAvatarCustom"] { display: none; }

    .chips { text-align: center; margin: 0.4rem 0 1.6rem; }
    .chips span {
        display: inline-block; margin: 0.25rem 0.2rem; padding: 0.3rem 0.8rem;
        border: 1px solid rgba(255, 255, 255, 0.16); border-radius: 999px;
        background: rgba(255, 255, 255, 0.04); color: #cfcfd6; font-size: 0.85rem;
    }

    .hero { text-align: center; margin: 2.5rem 0 1.5rem; }
    .hero h1 { font-size: 2.4rem; letter-spacing: -0.02em; margin-bottom: 0.2rem; }
    .hero p { color: #9a9aa2; margin: 0; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Har button ke 3 alag sawal hain, click par random ek chuna jata hai
STARTERS = [
    (
        "💡 Kuch samjhao",
        [
            "Explain how machine learning works in simple words.",
            "Explain what an API is, with a simple everyday example.",
            "Explain how neural networks learn, like I'm a beginner.",
        ],
    ),
    (
        "💻 Code likho",
        [
            "Write a Python function that checks if a number is prime.",
            "Write a Python function that reverses a string without slicing.",
            "Write a Python script that counts word frequency in a text file.",
        ],
    ),
    (
        "📅 Din plan karo",
        [
            "Help me plan a productive study day.",
            "Make me a simple weekly routine for learning Python and ML.",
            "Plan a 2-hour focused work session with short breaks.",
        ],
    ),
    (
        "🗣 Roman Urdu mein",
        [
            "Mujhe Roman Urdu mein 5 productivity tips do.",
            "Roman Urdu mein batao ke AI aur ML mein kya farq hai.",
            "Roman Urdu mein mujhe ek chhoti motivational kahani sunao.",
        ],
    ),
    (
        "🚀 Project idea",
        [
            "Give me 5 beginner ML project ideas for my GitHub.",
            "Suggest 5 NLP mini projects I can finish in a weekend.",
            "Give me 5 Streamlit app ideas that would look good in a portfolio.",
        ],
    ),
    (
        "✍️ Email likho",
        [
            "Write a short, polite email asking for a deadline extension.",
            "Write a professional email introducing myself to a recruiter.",
            "Write a short email following up on a job application.",
        ],
    ),
]

TTS_LANGUAGES = {"English": "en", "Urdu": "ur", "Hindi": "hi"}
IMAGE_TYPES = ["png", "jpg", "jpeg", "webp"]

# ---------- login (email + secret code) ----------
def log_in(email: str) -> None:
    for key in ("auth_step", "auth_email"):
        st.session_state.pop(key, None)
    st.session_state.user_email = email
    st.session_state.user_prefix = auth.user_prefix(email)
    st.rerun()


def render_login() -> None:
    # Login screen par sidebar nahi dikhana
    st.markdown(
        "<style>[data-testid='stSidebar'], [data-testid='stSidebarCollapsedControl']"
        " { display: none; }</style>",
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="hero">
            <h1>🤖 LLM Chat Hub</h1>
            <p>Apna AI assistant, sirf aap ke secret code ke peeche.</p>
        </div>
        <div class="chips">
            <span>🧠 Gemini + Groq</span><span>🖼 Image</span><span>📄 PDF par sawal</span>
            <span>🎤 Voice</span><span>🔧 Tools</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _, middle, _ = st.columns([1, 2, 1])
    with middle, st.container(border=True):
        step = st.session_state.get("auth_step", "email")

        if step == "email":
            st.subheader("👋 Welcome")
            with st.form("email_form"):
                email = st.text_input(
                    "Apna email likhein", placeholder="name@example.com", key="login_email"
                )
                go = st.form_submit_button("Continue →", type="primary")
            if go:
                email = auth.normalize_email(email)
                if auth.is_valid_email(email):
                    st.session_state.auth_email = email
                    st.session_state.auth_step = "code"
                    st.rerun()
                else:
                    st.error("Sahi email likhein, jaise name@example.com")
            return

        email = st.session_state.auth_email
        st.caption(f"📧 {email}")

        if auth.user_exists(email):
            st.subheader("🔑 Enter your code")
            with st.form("unlock_form"):
                code = st.text_input("Aap ka secret code", type="password", key="unlock_code")
                go = st.form_submit_button("Unlock 🔓", type="primary")
            if go:
                ok, message = auth.verify(email, code)
                if ok:
                    log_in(email)
                else:
                    st.error(message)
        else:
            st.subheader("✨ Apna secret code banayein")
            st.caption(
                "Ye aap ki pehli baar hai. Ye code sirf aap ko pata hona chahiye: "
                "har baar app kholne par yahi poocha jayega."
            )
            with st.form("signup_form"):
                code = st.text_input(
                    f"Naya secret code (kam az kam {auth.MIN_CODE_LENGTH} characters)",
                    type="password",
                    key="new_code",
                )
                confirm = st.text_input(
                    "Code dobara likhein", type="password", key="confirm_code"
                )
                invite = (
                    st.text_input("Invite code", type="password", key="invite_code")
                    if auth.signup_code_required()
                    else ""
                )
                go = st.form_submit_button("Account banayein ✨", type="primary")
            if go:
                if code != confirm:
                    st.error("Dono codes ek jaise nahi hain.")
                else:
                    ok, message = auth.register(email, code, invite)
                    if ok:
                        log_in(email)
                    else:
                        st.error(message)

        if st.button("← Email badlein"):
            st.session_state.pop("auth_step", None)
            st.session_state.pop("auth_email", None)
            st.rerun()


if "user_email" not in st.session_state:
    render_login()
    st.stop()

USER_PREFIX = st.session_state.user_prefix


# ---------- session state ----------
# Har user ki chats ke ids uske prefix se shuru hote hain, is liye sirf apni chats dikhti hain
def new_chat_id() -> str:
    return f"{USER_PREFIX}{chat_store.new_chat_id()}"


def user_chats() -> list[dict]:
    return [c for c in chat_store.list_chats() if c["id"].startswith(USER_PREFIX)]


if "chat_id" not in st.session_state:
    st.session_state.chat_id = new_chat_id()
    st.session_state.messages = []
st.session_state.setdefault("voice_n", 0)  # recording widget reset karne ke liye
st.session_state.setdefault("image_n", 0)  # image uploader reset karne ke liye


def start_new_chat() -> None:
    st.session_state.chat_id = new_chat_id()
    st.session_state.messages = []


def open_chat(chat_id: str) -> None:
    if not chat_id.startswith(USER_PREFIX):
        return
    data = chat_store.load_chat(chat_id)
    if data:
        st.session_state.chat_id = chat_id
        st.session_state.messages = data["messages"]


# ---------- sidebar ----------
with st.sidebar:
    st.caption(f"👤 {st.session_state.user_email}")
    if st.button("🔒 Lock / Logout", width="stretch"):
        st.session_state.clear()  # sab kuch saaf, agli baar phir code poocha jayega
        st.rerun()

    st.divider()
    st.header("🧠 Model")
    provider = st.selectbox(
        "Kon sa model use karna hai?",
        PROVIDERS,
        key="provider",
        label_visibility="collapsed",
    )
    st.caption(f"{provider} · {model_name(provider)}")

    st.divider()
    st.header("💬 Chats")
    if st.button("➕ New chat", width="stretch", type="primary"):
        start_new_chat()
        st.rerun()

    saved = user_chats()
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
    st.header("🧰 Features")

    use_tools = st.toggle(
        "🔧 Tools (calculator + web search)",
        help="Model zaroorat par calculator ya web search khud chalayega.",
    )

    with st.expander("🖼 Image"):
        image_file = st.file_uploader(
            "Agle sawal ke saath image bhejein",
            type=IMAGE_TYPES,
            key=f"image_{st.session_state.image_n}",
        )
        if image_file:
            st.image(image_file, width=160)
            if not supports_images(provider):
                st.warning(
                    f"{provider} images support nahi karta. "
                    "Gemini ya Groq chunein."
                )

    with st.expander("📄 Documents (RAG)"):
        doc_files = st.file_uploader(
            "PDF / TXT / MD upload karein",
            type=["pdf", "txt", "md"],
            accept_multiple_files=True,
            key="docs",
        )
        docs_key = tuple((f.name, f.size) for f in doc_files)
        if docs_key != st.session_state.get("docs_key"):
            if doc_files:
                with st.spinner("Documents index ho rahe hain..."):
                    st.session_state.doc_index = rag.DocIndex(
                        [(f.name, f.getvalue()) for f in doc_files]
                    )
            else:
                st.session_state.doc_index = None
            st.session_state.docs_key = docs_key

        doc_index = st.session_state.get("doc_index")
        if doc_files and doc_index is not None:
            if doc_index.chunks:
                st.caption(f"📚 {len(doc_index.chunks)} hisse tayyar, ab sawal poochein.")
            else:
                st.warning(
                    "In files mein text nahi mila (shayad scanned PDF hai)."
                )

    with st.expander("🎤 Voice"):
        voice_clip = st.audio_input(
            "Bol kar poochein", key=f"voice_{st.session_state.voice_n}"
        )
        speak_reply = st.toggle("🔊 Jawab bolkar sunao")
        tts_language = st.selectbox("Awaaz ki zubaan", list(TTS_LANGUAGES))
        st.caption("Voice input ke liye GROQ_API_KEY zaroori hai.")

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

# Voice: nayi recording ho to usay text mein badal kar prompt bana do
if voice_clip is not None and not prompt:
    try:
        with st.spinner("Awaaz sun raha hoon..."):
            prompt = voice.transcribe(create_client("Groq"), voice_clip.getvalue())
    except Exception as exc:  # noqa: BLE001
        st.error(f"Voice samajh nahi aayi: {exc}")
    finally:
        st.session_state.voice_n += 1  # agli baar recording widget khali ho jaye
    prompt = prompt or None

if not st.session_state.messages and not prompt:
    st.markdown(
        f"""
        <div class="hero">
            <h1>🤖 LLM Assistant</h1>
            <p>Powered by {provider} · {model_name(provider)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    cols = st.columns(2)
    for i, (label, variants) in enumerate(STARTERS):
        if cols[i % 2].button(label, key=f"starter_{i}", width="stretch"):
            st.session_state.pending_prompt = random.choice(variants)
            st.rerun()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Pichle jawab ki awaaz (agar "Jawab bolkar sunao" on tha)
if "tts_audio" in st.session_state:
    st.audio(st.session_state.pop("tts_audio"), format="audio/mp3", autoplay=True)
if "tts_error" in st.session_state:
    st.caption(f"🔇 Awaaz nahi ban saki: {st.session_state.pop('tts_error')}")

if prompt:
    # Image sirf isi sawal ke saath jati hai
    image = None
    if image_file:
        if supports_images(provider):
            image = (image_file.getvalue(), image_file.type or "image/png")
        else:
            st.warning(f"{provider} images support nahi karta, image nahi bheji gayi.")

    with st.chat_message("user"):
        if image:
            st.image(image[0], width=240)
        st.markdown(prompt)

    request_messages = [
        *st.session_state.messages,
        {"role": "user", "content": prompt},
    ]

    # RAG: relevant document hisse is sawal ke system prompt mein jodo
    effective_system = system_prompt
    index = st.session_state.get("doc_index")
    if index is not None and index.chunks:
        context = rag.build_context(index, prompt)
        if context:
            effective_system = f"{system_prompt}\n\n{context}"

    with st.chat_message("assistant"):
        try:
            reply = st.write_stream(
                stream_reply(
                    client,
                    request_messages,
                    effective_system,
                    provider,
                    image=image,
                    use_tools=use_tools,
                )
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
            # History mein image ke bytes nahi, sirf nishani save hoti hai
            saved_prompt = f"🖼 [image attached] {prompt}" if image else prompt
            st.session_state.messages.extend(
                [
                    {"role": "user", "content": saved_prompt},
                    {"role": "assistant", "content": reply},
                ]
            )
            chat_store.save_chat(
                st.session_state.chat_id, st.session_state.messages
            )
            if image:
                st.session_state.image_n += 1  # uploader khali karo

            if speak_reply:
                try:
                    st.session_state.tts_audio = voice.speak(
                        str(reply), TTS_LANGUAGES[tts_language]
                    )
                except Exception as exc:  # noqa: BLE001
                    st.session_state.tts_error = str(exc)

            st.rerun()  # refresh sidebar so the chat title appears