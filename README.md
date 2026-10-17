# LLM Chat Hub: naye features

| Feature | Kahan se aata hai | Note |
|---|---|---|
| 🖼 Image support | Gemini, Groq (vision model), Mistral | Image sirf usi sawal ke saath jati hai |
| 📄 RAG (PDF/TXT/MD) | `rag.py` (TF-IDF, scikit-learn) | Koi extra API key nahi chahiye |
| 🎤 Voice input | Groq Whisper | `GROQ_API_KEY` zaroori |
| 🔊 Voice output | gTTS | Internet chahiye |
| 🔧 Tools | `tools.py` (calculator, web search) | Sidebar ka toggle |
| 🌍 Zyada providers | OpenRouter, Mistral | Key `.env` mein daalein |
| ☁️ Deploy | Streamlit Community Cloud | Neeche steps |

## Local chalana
```
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Community Cloud par deploy
1. Code GitHub par push karein (`.env` push nahi karna).
2. share.streamlit.io par repo chunein, main file `app.py`.
3. App settings > Secrets mein keys daalein:
```
GEMINI_API_KEY = "..."
GROQ_API_KEY = "..."
```
4. Deploy dabayein.

Note: Cloud par `chats/` folder restart ke baad khali ho sakta hai (saved chats permanent nahi rehtin).