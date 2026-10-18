# 🤖 LLM Chat Hub

Multi-model AI chat app jo **Python + Streamlit** se bani hai. Is mein email + secret code ka login hai, har user ki apni chats hain, aur Gemini, Groq (aur Mistral / OpenRouter) ke saath **image input, PDF par sawal (RAG), voice aur tools** (calculator + web search) bhi hain.

> Ye mera seekhne ka safar hai. Feedback aur suggestions ka bahut shukriya! ⭐

## ✨ Features

| Feature | Kya karta hai |
|---|---|
| 🔐 **Secure login** | Email + secret code, code hashed save hota hai, 5 ghalat koshishon par lock |
| 👤 **Per-user chats** | Har user ko sirf apni chats dikhti hain |
| 🧠 **Model switcher** | Gemini, Groq, aur (key hone par) Mistral / OpenRouter ke beech ek click mein switch |
| ⚡ **Streaming** | Jawab word-by-word screen par aata hai |
| 💬 **Multi-turn memory** | Assistant pichli baatein yaad rakhta hai |
| 🗂 **Chat history** | Chats save hoti hain, sidebar se kholein, delete karein, New chat banayein |
| 🚀 **Starter suggestions** | 6 buttons, click par har baar alag sawal |
| 🎭 **Customizable personality** | Settings se system prompt badal kar assistant ka style badlein |
| 🖼 **Image input** | Image bhej kar us ke baare mein poochein |
| 📄 **RAG (PDF / TXT / MD)** | Apne documents upload karein aur un par sawal poochein ("pehli 3 slides", "page 5" jaise sawal bhi) |
| 🎤 **Voice input** | Bol kar poochein (Groq Whisper) |
| 🔊 **Voice output** | Jawab bolkar sunein (English, Urdu, Hindi) |
| 🔧 **Tools** | Calculator aur web search, model zaroorat par khud chalata hai |
| 🔄 **Auto retry** | Model busy ho (503 / 429) to app khud dobara koshish karti hai |
| 🖤 **Dark theme** | Black gradient design |

## 🛠 Tech stack

| Cheez | Kaam |
|---|---|
| Python | Main language |
| Streamlit | Web interface |
| google-genai | Gemini API |
| groq | Groq API aur Whisper (voice to text) |
| openai (SDK) | Mistral aur OpenRouter se baat karne ke liye |
| scikit-learn | RAG mein TF-IDF search |
| pypdf | PDF se text nikalna |
| gTTS | Text to speech |
| ddgs | Web search tool |
| python-dotenv | API keys ko safe rakhna |

## 📁 Project structure

```
llm-chat-hub-secure/
├── app.py            # Streamlit UI (login, chat, sidebar)
├── auth.py           # Email + secret code login
├── assistant.py      # Models, streaming, retry, tool loop
├── tools.py          # Calculator + web search
├── rag.py            # Documents par sawal (RAG)
├── voice.py          # Voice input / output
├── chat_store.py     # Chats ko JSON mein save karna
├── chatbot_cli.py    # Terminal version
├── requirements.txt
└── .env.example
```

## 🚀 Setup (local)

**1. Repo clone karein**
```bash
git clone https://github.com/muattarnaz7-svg/llm-chat-hub-secure.git
cd llm-chat-hub-secure
```

**2. Virtual environment banayein**
```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac / Linux
```

**3. Packages install karein**
```bash
pip install -r requirements.txt
```

**4. API keys daalein**

`.env.example` ko copy karke `.env` naam se save karein:
```env
GEMINI_API_KEY=your_key_here
GROQ_API_KEY=your_key_here

# Optional: extra providers (key daalte hi sidebar mein dikhne lagte hain)
# MISTRAL_API_KEY=
# OPENROUTER_API_KEY=
```

Free keys: Gemini (Google AI Studio) aur Groq (console.groq.com) se mil jati hain.

**5. App chalayein**
```bash
streamlit run app.py
```

## 📖 Use kaise karein

### 🔐 Login
1. App khulte hi **email** poochti hai.
2. **Pehli baar:** "Apna secret code banayein" aata hai. Kam az kam 6 characters ka code, do baar likhein.
3. **Agli baar:** "Enter your code" aata hai. Wahi code likhein jo aap ne banaya tha.
4. Page dobara khulne par code phir poocha jata hai. Sidebar mein **🔒 Lock / Logout** se bhi lock kar sakte hain.

### 🧠 Model chunna
Sidebar ke **Model** dropdown se Gemini ya Groq chunein. Mistral aur OpenRouter tab dikhte hain jab `.env` mein un ki key ho.

### 🖼 Image bhejna
Sidebar mein **Image** kholein, photo upload karein, aur chat mein sawal likhein (jaise "Is image mein kya hai?"). Image sirf usi sawal ke saath jati hai.

### 📄 Apne documents par sawal (RAG)
1. **Documents (RAG)** kholein aur PDF / TXT / MD upload karein.
2. "hisse tayyar" likha aane ke baad sawal poochein: "Is document mein dropout kya hai?" ya "pehli 3 slides mein kya hai?"

### 🎤 / 🔊 Voice
- **Input:** Voice kholein, mic dabayein, bolein aur stop karein. Awaaz khud text ban kar sawal ban jati hai.
- **Output:** **Jawab bolkar sunao** on karein aur awaaz ki zubaan chunein.

### 🔧 Tools
**Tools** toggle on karein. Phir poochein: "1234 * 5678 + sqrt(144) kitna hota hai?" ya "Streamlit ki latest news batao".

## ⚙️ Settings (`.env`)

| Variable | Matlab |
|---|---|
| `GEMINI_API_KEY` / `GROQ_API_KEY` | Zaroori (kam az kam ek) |
| `MISTRAL_API_KEY` / `OPENROUTER_API_KEY` | Optional extra providers |
| `GEMINI_MODEL`, `GROQ_MODEL`, `GROQ_VISION_MODEL` | Model naam badalne ke liye |
| `SIGNUP_CODE` | Set ho to naya account sirf wahi bana sakta hai jise ye invite code pata ho |
| `USERS_FILE` | Users ki file ka path (default: `users.json`) |

## 🔒 Security ke baare mein

- Secret code kabhi seedha save nahi hota, sirf **salt ke saath hash** (PBKDF2) `users.json` mein jata hai.
- 5 ghalat koshishon ke baad 5 minute ka lock lag jata hai.
- **`.env` aur `users.json` ko GitHub par push na karein** (`.gitignore` mein dono hone chahiye).
- Email verify nahi hota, ye sirf pehchan ka naam hai. Code bhool jaye to us user ki entry `users.json` se hata dein, wo naya code bana lega.
- Public deploy par `SIGNUP_CODE` zaroor set karein, warna koi bhi naya account bana kar aap ki API quota use kar sakta hai.

## ☁️ Streamlit Community Cloud par deploy

1. Code GitHub par push karein (`.env` aur `users.json` push nahi karne).
2. [share.streamlit.io](https://share.streamlit.io) par repo chunein, main file `app.py`.
3. App settings > Secrets mein keys daalein:
   ```toml
   GEMINI_API_KEY = "..."
   GROQ_API_KEY = "..."
   SIGNUP_CODE = "koi_secret_lafz"
   ```
4. Deploy dabayein.

> **Note:** Cloud par `chats/` aur `users.json` restart ke baad khali ho sakte hain, yani saved chats aur accounts permanent nahi rehte. Permanent storage ke liye database chahiye.

## ⚠️ Abhi ki limitations

- History mein image ke bytes save nahi hote, is liye model ko agle sawalon par purani image nahi dikhti.
- RAG lafzon par match karta hai, matlab par nahi. Roman Urdu sawal aur English document ka match kamzor ho sakta hai.
- Scanned PDF (sirf images wali) se text nahi nikalta.
- Login file based hai, bohat bare paimane par istemal ke liye database aur email verification chahiye.

## 🗺 Aage ka plan

- [ ] RAG ko embeddings se behtar banana
- [ ] Poore document ka summary feature
- [ ] Streamlit Cloud par live deploy
- [ ] Chats aur users ko database mein save karna
- [ ] Stats wala dashboard (chats, models ka istemal)

## 🤝 Contribute

Suggestions, issues aur pull requests ka swagat hai. Pasand aaye to ⭐ star zaroor dein!

## 👤 Author

**muattarnaz7-svg**: [GitHub](https://github.com/muattarnaz7-svg)