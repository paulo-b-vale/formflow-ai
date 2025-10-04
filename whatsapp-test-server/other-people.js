const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const axios = require('axios');

// --- CONFIGURATION ---
// The API_ENDPOINT now points to the service name in docker-compose
const API_ENDPOINT = "http://app:8000";
let bearerToken = null; // We will store the auth token here

// --- WHATSAPP CLIENT SETUP ---
const client = new Client({
    // Store session data in a volume
    authStrategy: new LocalAuth({
        clientId: "ai-form-assistant-test",
        dataPath: "/usr/src/app/session_data"
    }),
    puppeteer: {
        headless: true,
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu'
        ]
    }
});

// --- WHATSAPP EVENT HANDLERS ---
client.on('qr', (qr) => {
    console.log("--------------------------------------------------");
    console.log("Scan this QR code with your WhatsApp app:");
    qrcode.generate(qr, { small: true });
    console.log("--------------------------------------------------");
});

client.on('ready', () => {
    console.log('✅ WhatsApp client is ready!');
    console.log('🤖 Send a message to get started. Type "login" or "register".');
});

client.on('authenticated', () => {
    console.log('✅ Authenticated with WhatsApp!');
});

client.on('auth_failure', (msg) => {
    console.error('❌ Authentication failed:', msg);
});

client.on('disconnected', (reason) => {
    console.log('❌ Client was disconnected:', reason);
    bearerToken = null; // Clear token on disconnect
});

// --- MESSAGE PROCESSING LOGIC ---
client.on('message', async (message) => {
    const fromNumber = message.from;
    const msgBody = message.body.trim();
    console.log(`\n📲 Message from ${fromNumber}: "${msgBody}"`);

    // --- Login & Registration Flow (simplified) ---
    if (!bearerToken) {
        if (msgBody.toLowerCase().startsWith('register')) {
            // Format: register <name> <email> <password>
            const [, name, email, password] = msgBody.split(' ');
            if (!name || !email || !password) {
                client.sendMessage(fromNumber, "To register, please use the format:\n`register <Your Name> <your@email.com> <password>`");
                return;
            }
            try {
                const payload = { name, email, password, "phone_number": fromNumber.split('@')[0] };
                await axios.post(`${API_ENDPOINT}/auth/register`, payload);
                client.sendMessage(fromNumber, "✅ Registration successful! Now, please log in using:\n`login <password>`");
            } catch (error) {
                const errorMsg = error.response?.data?.detail || "Could not register.";
                client.sendMessage(fromNumber, `❌ Registration failed: ${errorMsg}`);
            }
        } else if (msgBody.toLowerCase().startsWith('login')) {
            // Format: login <password>
            const [, password] = msgBody.split(' ');
            if (!password) {
                client.sendMessage(fromNumber, "To log in, please use the format:\n`login <password>`");
                return;
            }
            try {
                const payload = { "phone_number": fromNumber.split('@')[0], password };
                const res = await axios.post(`${API_ENDPOINT}/auth/phone-login`, payload);
                bearerToken = res.data.tokens.access_token;
                client.sendMessage(fromNumber, "✅ Login successful! How can I help you today?");
            } catch (error) {
                client.sendMessage(fromNumber, "❌ Login failed. Please check your password or register first.");
            }
        } else {
            client.sendMessage(fromNumber, "Welcome! Please start by sending `register <name> <email> <password>` or `login <password>`.");
        }
        return;
    }

    // --- Authenticated Conversation Flow ---
    try {
        const payload = { "user_input": msgBody };
        const headers = { "Authorization": `Bearer ${bearerToken}` };
        const res = await axios.post(`${API_ENDPOINT}/conversation/message`, payload, { headers });

        const reply = res.data.message || "I'm not sure how to respond to that.";
        client.sendMessage(fromNumber, reply);

    } catch (error) {
        if (error.response?.status === 401) {
            bearerToken = null; // Token expired or invalid
            client.sendMessage(fromNumber, "Your session has expired. Please `login` again.");
        } else {
            console.error("API Error:", error.response?.data || error.message);
            client.sendMessage(fromNumber, "Sorry, an error occurred while processing your request.");
        }
    }
});

// --- START THE CLIENT ---
console.log("🚀 Initializing WhatsApp Test Server...");
client.initialize();