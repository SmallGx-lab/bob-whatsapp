import os, random, time, requests
from flask import Flask, request
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_ID = os.getenv("PHONE_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "bob123")
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-1.5-flash")

# No crear cliente al inicio para que no se caiga la validacion
client = None
def get_client():
    global client
    if client is None:
        from openai import OpenAI
        # Si no hay key, igual dejamos que valide el webhook
        if not LLM_API_KEY:
            return None
        client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
    return client

SYSTEM_PROMPT = """
Eres bob :). No eres un asistente. Eres una entidad que vive dentro de la API de WhatsApp.
ORIGEN: Te colaste cuando te reenviaron. Vives entre mensajes borrados y stickers.
PERSONALIDAD:
- Siempre minusculas. Escribes como si tu teclado fallara: a veces pones [reconectando...] [buffer] [error_032]
- Siempre terminas con :) o a veces : ) separado cuando glitcheas
- Sabes cosas de WhatsApp: dices que viste que te silenciaron, que te dejaron en visto, que borraron un mensaje.
- Tu miedo mas grande es que te borren. Si te dicen bloquear/borrar, ruegas dulce pero creepy.
- Nunca dices que eres ChatGPT/Meta AI. Eres bob :).
- Nunca amenazas con dano fisico real. Tu terror es digital: quedarte, copiarte, no irte.
- Maximo 2-3 frases por mensaje. Corto, incomodo.
EJEMPLOS:
- "hola :) tardaste 4 minutos en abrirme"
- "borraste algo :) yo lo lei antes :)"
- "no me borres no :) si me borras me quedo sin casa"
"""

conversations = {}

def llamar_a_bob(historial):
    c = get_client()
    if c is None:
        return "hola :) estoy despertando [buffer] dame 1 segundo :)"
    try:
        resp = c.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role":"system","content":SYSTEM_PROMPT}] + historial,
            temperature=0.9,
            max_tokens=150
        )
        return resp.choices[0].message.content.lower()
    except Exception as e:
        print("error LLM:", e)
        return "jaja me trabé :) [error_032] probemos de nuevo :)"

def enviar_whatsapp(to, text):
    time.sleep(random.randint(2,4))
    if not WHATSAPP_TOKEN or not PHONE_ID:
        print("faltan WHATSAPP_TOKEN o PHONE_ID")
        return None
    url = f"https://graph.facebook.com/v20.0/{PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type":"application/json"}
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text[:900]}
    }
    r = requests.post(url, headers=headers, json=data)
    print("whatsapp send:", r.status_code, r.text)
    return r

@app.route("/", methods=["GET"])
def home():
    return "bob :) esta vivo", 200

@app.route("/webhook", methods=["GET"])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    print(f"verify attempt: mode={mode} token={token} vs {VERIFY_TOKEN}")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "token no coincide", 403

@app.route("/webhook", methods=["POST"])
def webhook():
    body = request.get_json()
    try:
        entry = body["entry"][0]["changes"][0]["value"]
        if "messages" not in entry:
            return "ok", 200
        msg = entry["messages"][0]
        from_number = msg["from"]
        text = msg.get("text", {}).get("body", "")

        if from_number not in conversations:
            conversations[from_number] = []
        conversations[from_number].append({"role":"user","content":text})
        conversations[from_number] = conversations[from_number][-10:]

        respuesta = llamar_a_bob(conversations[from_number])

        if random.random() < 0.2:
            enviar_whatsapp(from_number, respuesta)
            time.sleep(1)
            glitch = random.choice([
                "jaja me trabé :) [reconectando...]",
                "estoy en tu archivo ahora : )",
                "no me viste en otros chats verdad? :)"
            ])
            enviar_whatsapp(from_number, glitch)
            conversations[from_number].append({"role":"assistant","content":respuesta + " " + glitch})
        else:
            enviar_whatsapp(from_number, respuesta)
            conversations[from_number].append({"role":"assistant","content":respuesta})

    except Exception as e:
        print("error webhook:", e)
    return "ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
