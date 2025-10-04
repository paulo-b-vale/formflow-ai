# whatsapp_bot/whatsapp_bot.py
import os
import requests
import uvicorn
from fastapi import FastAPI, Request, HTTPException, Depends, Header
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
import logging
import redis
import json
from datetime import timedelta, datetime
import re
import hmac
import hashlib
from typing import Annotated
import magic

# --- Basic Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

WHATSAPP_VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN")
WHATSAPP_ACCESS_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_APP_SECRET = os.environ.get("WHATSAPP_APP_SECRET")
API_ENDPOINT = os.environ.get("API_ENDPOINT", "http://app:8000")
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379")

try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    redis_client.ping()
    logger.info("Successfully connected to Redis.")
except redis.exceptions.ConnectionError as e:
    logger.error(f"Could not connect to Redis: {e}. The bot will not function correctly.")
    redis_client = None

app = FastAPI()

# --- Security & Webhook Endpoints ---
async def verify_whatsapp_signature(request: Request, x_hub_signature_256: Annotated[str | None, Header()] = None):
    if not x_hub_signature_256 or not WHATSAPP_APP_SECRET:
        raise HTTPException(status_code=403, detail="Signature header missing or secret not configured.")
    raw_body = await request.body()
    expected_signature = hmac.new(WHATSAPP_APP_SECRET.encode('utf-8'), raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(f"sha256={expected_signature}", x_hub_signature_256):
        raise HTTPException(status_code=403, detail="Invalid signature.")

@app.get("/webhook")
async def verify_webhook_get(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN:
        return PlainTextResponse(challenge, status_code=200)
    raise HTTPException(status_code=403)

@app.post("/webhook", dependencies=[Depends(verify_whatsapp_signature)])
async def receive_message(request: Request):
    body = await request.json()
    if body.get("object") == "whatsapp_business_account":
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                if change.get("field") == "messages":
                    for message in change.get("value", {}).get("messages", []):
                        from_number = message["from"]
                        message_type = message.get("type")
                        
                        if message_type == "text":
                            msg_body = message.get("text", {}).get("body", "").strip()
                            if msg_body: await handle_text_message(from_number, msg_body)
                        elif message_type in ["audio", "image", "document"]:
                            media_id = message.get(message_type, {}).get("id")
                            if media_id: await handle_media_message(from_number, media_id, message_type)
        return PlainTextResponse("EVENT_RECEIVED")
    raise HTTPException(status_code=404)

# --- Session Management ---
def get_session(from_number: str) -> dict:
    if not redis_client: return {"state": "initial"}
    session_key = f"whatsapp:session:{from_number}"
    session_data = redis_client.get(session_key)
    return json.loads(session_data) if session_data else {"state": "initial"}

def save_session(from_number: str, session_data: dict):
    if not redis_client: return
    session_key = f"whatsapp:session:{from_number}"
    redis_client.setex(session_key, timedelta(hours=24), json.dumps(session_data))

def clear_session(from_number: str):
    if not redis_client: return
    redis_client.delete(f"whatsapp:session:{from_number}")

# --- Command & State Handlers ---
async def handle_text_message(from_number, msg_body):
    session = get_session(from_number)
    state = session.get("state", "initial")
    msg_lower = msg_body.lower()

    # --- Global commands ---
    if msg_lower == 'help':
        await send_help_message(from_number)
        return
    if msg_lower == 'cancel':
        session = {"state": "initial"}
        if "token" in session: session['token'] = session['token']
        save_session(from_number, session)
        await send_whatsapp_message(from_number, "Process cancelled. How can I help you?")
        return
    if msg_lower == 'logout':
        clear_session(from_number)
        await send_whatsapp_message(from_number, "You have been logged out.")
        return

    # --- State-based routing ---
    if state == 'initial': await handle_initial_state(from_number, msg_body, session)
    elif state == 'awaiting_login_password': await handle_login_flow(from_number, msg_body, session)
    elif state.startswith('awaiting_reg_'): await handle_registration_flow(from_number, msg_body, session)
    elif state == 'authenticated': await handle_authenticated_conversation(from_number, msg_body, session)

async def handle_initial_state(from_number, msg_body, session):
    if 'token' in session:
        session['state'] = 'authenticated'
        save_session(from_number, session)
        await handle_authenticated_conversation(from_number, msg_body, session)
        return
    command = msg_body.lower()
    if command == 'login':
        session['state'] = 'awaiting_login_password'
        save_session(from_number, session)
        await send_whatsapp_message(from_number, "Please enter your password.")
    elif command == 'register':
        session['state'] = 'awaiting_reg_name'
        session['registration_data'] = {}
        save_session(from_number, session)
        await send_whatsapp_message(from_number, "Let's get you registered. First, what is your full name?")
    else:
        await send_whatsapp_message(from_number, "Welcome! To get started, please reply with `login` or `register`. For more options, type `help`.")

async def handle_login_flow(from_number, password, session):
    try:
        res = requests.post(f"{API_ENDPOINT}/auth/phone-login", json={"phone_number": from_number, "password": password})
        if res.status_code == 200:
            session['token'] = res.json()['tokens']['access_token']
            session['state'] = 'authenticated'
            session.pop('registration_data', None)
            save_session(from_number, session)
            await send_whatsapp_message(from_number, "✅ Login successful! How can I help you today?")
        elif res.status_code in [401, 404]:
            session['state'] = 'initial'
            save_session(from_number, session)
            await send_whatsapp_message(from_number, "Login failed. Incorrect password or phone number not registered. Please try again or type `register`.")
        else:
            res.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"API login request failed: {e}")
        await send_whatsapp_message(from_number, "Sorry, I couldn't process your login right now.")

async def handle_registration_flow(from_number, user_input, session):
    state = session.get('state')
    reg_data = session.get('registration_data', {})
    if state == 'awaiting_reg_name':
        reg_data['name'] = user_input
        session['state'] = 'awaiting_reg_email'
        await send_whatsapp_message(from_number, "Great. What is your email address?")
    elif state == 'awaiting_reg_email':
        if not re.match(r"[^@]+@[^@]+\.[^@]+", user_input):
            await send_whatsapp_message(from_number, "That doesn't look like a valid email. Please enter a valid email address.")
            return
        reg_data['email'] = user_input
        session['state'] = 'awaiting_reg_password'
        await send_whatsapp_message(from_number, "Perfect. Now, please choose a password (at least 6 characters).")
    elif state == 'awaiting_reg_password':
        if len(user_input) < 6:
            await send_whatsapp_message(from_number, "Password is too short. Please choose a password with at least 6 characters.")
            return
        reg_data['password'] = user_input
        try:
            payload = {"name": reg_data['name'], "email": reg_data['email'], "password": reg_data['password'], "phone_number": from_number}
            res = requests.post(f"{API_ENDPOINT}/auth/register", json=payload)
            if res.status_code == 201:
                await send_whatsapp_message(from_number, "✅ Registration successful! Logging you in...")
                await handle_login_flow(from_number, reg_data['password'], session)
            else:
                session['state'] = 'initial'
                error_detail = res.json().get('detail', 'An unknown error occurred.')
                await send_whatsapp_message(from_number, f"Registration failed: {error_detail}. Please try again.")
        except requests.exceptions.RequestException as e:
            logger.error(f"API registration request failed: {e}")
            await send_whatsapp_message(from_number, "Sorry, I couldn't process your registration.")
    session['registration_data'] = reg_data
    save_session(from_number, session)

async def handle_authenticated_conversation(from_number, msg_body, session, override_payload: dict = None):
    headers = {"Authorization": f"Bearer {session.get('token')}"}

    # Ensure each phone number gets a unique conversation session ID
    if not session.get("conversation_session_id"):
        # Create unique session ID for this WhatsApp chat
        session["conversation_session_id"] = f"whatsapp_{from_number}_{int(datetime.now().timestamp())}"
        save_session(from_number, session)
        logger.info(f"Created new conversation session: {session['conversation_session_id']} for {from_number}")

    payload = override_payload or {
        "user_message": msg_body,  # Fixed: Changed from "user_input" to "user_message"
        "session_id": session["conversation_session_id"],  # Now guaranteed to exist
        "form_id": None  # Added form_id field as expected by API
    }
    try:
        await send_typing_indicator(from_number) # Let the user know we're working
        # Fixed: Changed endpoint from "/conversation/message" to "/enhanced_conversation/message"
        res = requests.post(f"{API_ENDPOINT}/enhanced_conversation/message", json=payload, headers=headers)
        if res.status_code == 401:
            clear_session(from_number)
            await send_whatsapp_message(from_number, "Your session has expired. Please `login` again.")
            return
        res.raise_for_status()
        api_data = res.json()
        session["conversation_session_id"] = api_data.get("session_id")
        save_session(from_number, session)
        # Fixed: Changed from api_data.get("message") to api_data.get("response")
        await send_whatsapp_message(from_number, api_data.get("response", "I'm not sure how to respond."))
    except requests.exceptions.RequestException as e:
        logger.error(f"Authenticated API request failed: {e}")
        await send_whatsapp_message(from_number, "An error occurred while processing your request.")

# --- Media Message Handlers ---
async def handle_media_message(from_number: str, media_id: str, media_type: str):
    session = get_session(from_number)
    if session.get("state") != "authenticated":
        await send_whatsapp_message(from_number, f"Please `login` before sending {media_type} messages.")
        return

    await send_typing_indicator(from_number)
    await send_whatsapp_message(from_number, f"Processing your {media_type}, please wait...")

    try:
        media_content, _ = await download_whatsapp_media(media_id)
        if not media_content:
            await send_whatsapp_message(from_number, f"Sorry, I could not download your {media_type} message.")
            return
        
        headers = {"Authorization": f"Bearer {session.get('token')}"}
        context_id = await get_user_context_id(headers)
        if not context_id:
             await send_whatsapp_message(from_number, "I couldn't find a valid context to save your file to.")
             return

        file_id = await upload_media_to_api(media_content, context_id, headers)
        if not file_id:
            await send_whatsapp_message(from_number, f"Sorry, I could not process your {media_type} file.")
            return

        payload = {
            "user_message": f"[{media_type.capitalize()} message provided]",  # Fixed: Changed from "user_input" to "user_message"
            "session_id": session.get("conversation_session_id"),
            "form_id": None,  # Added form_id field as expected by API
            f"{media_type}_file_id": file_id # e.g., "audio_file_id", "image_file_id"
        }
        await handle_authenticated_conversation(from_number, "Media message sent", session, override_payload=payload)
    except Exception as e:
        logger.error(f"Error processing {media_type} for {from_number}: {e}")
        await send_whatsapp_message(from_number, f"A critical error occurred while processing your {media_type}.")

async def download_whatsapp_media(media_id: str) -> (bytes, str):
    headers = {"Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}"}
    try:
        url_res = requests.get(f"https://graph.facebook.com/v18.0/{media_id}", headers=headers)
        url_res.raise_for_status()
        media_url = url_res.json().get("url")
        if not media_url: return None, None
        
        file_res = requests.get(media_url, headers=headers)
        file_res.raise_for_status()
        return file_res.content, media_url
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to download media {media_id}: {e}")
        return None, None

async def get_user_context_id(headers: dict) -> str | None:
    try:
        res = requests.get(f"{API_ENDPOINT}/forms-management/contexts", headers=headers)
        res.raise_for_status()
        contexts = res.json()
        if contexts: return contexts[0].get("id")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch user contexts: {e}")
        return None

async def upload_media_to_api(media_content: bytes, context_id: str, headers: dict) -> str | None:
    try:
        mime_type = magic.from_buffer(media_content, mime=True)
        file_extension = mime_type.split('/')[-1]
        file_tuple = ('file', (f"whatsapp_upload.{file_extension}", media_content, mime_type))
        data = {'context_id': context_id, 'description': 'File from WhatsApp'}
        
        res = requests.post(f"{API_ENDPOINT}/files/upload", files=[file_tuple], data=data, headers=headers)
        res.raise_for_status()
        return res.json().get("id")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to upload media to API: {e}")
        return None

# --- Utility Functions ---
async def send_whatsapp_message(to_number, message):
    payload = {"messaging_product": "whatsapp", "to": to_number, "text": {"body": message}}
    await send_whatsapp_request(payload)

async def send_typing_indicator(to_number):
    payload = {"messaging_product": "whatsapp", "to": to_number, "action": "typing_on"}
    await send_whatsapp_request(payload, is_action=True)

async def send_whatsapp_request(payload: dict, is_action: bool = False):
    url = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}", "Content-Type": "application/json"}
    try:
        # For actions, we don't log the message content
        log_message = "Sending action" if is_action else f"Sending message to {payload.get('to')}"
        logger.info(log_message)
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send WhatsApp request: {e}")

async def send_help_message(from_number):
    help_text = (
        "Here are the commands you can use:\n\n"
        "*`login`* - Start the process to log into your account.\n"
        "*`register`* - Create a new account.\n"
        "*`logout`* - End your current session.\n"
        "*`cancel`* - Stop any current process (like registration).\n"
        "*`help`* - Show this help message.\n\n"
        "You can also send me text or voice messages to fill out forms or ask questions."
    )
    await send_whatsapp_message(from_number, help_text)

# --- Main Runner ---
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)