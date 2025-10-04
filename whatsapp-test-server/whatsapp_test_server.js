const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const axios = require('axios');

// --- CONFIGURATION ---
const API_ENDPOINT = "http://app:8000";
const MY_NUMBER = "contry_cod,regional_code,number,no_caracteres@c.us"; // Your WhatsApp number
const SESSION_DATA_PATH = "/usr/src/app/session_data";

// --- ENHANCED STATE MANAGEMENT ---
let isAuthenticated = false;
let bearerToken = null;
let isProcessing = false;

// User conversation states for multi-step flows
let userStates = new Map(); // Will store conversation state per user

// Session ID for enhanced conversation continuity
let conversationSessionId = null;

// Conversation states
const STATES = {
    IDLE: 'idle',
    REGISTRATION_NAME: 'registration_name',
    REGISTRATION_EMAIL: 'registration_email', 
    REGISTRATION_PASSWORD: 'registration_password',
    LOGIN_PASSWORD: 'login_password'
};

// --- WHATSAPP CLIENT SETUP ---
const client = new Client({
    authStrategy: new LocalAuth({
        clientId: "ai-form-assistant-test",
        dataPath: SESSION_DATA_PATH
    }),
    puppeteer: {
        headless: true,
        executablePath: '/usr/bin/google-chrome-stable',
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu'
        ]
    }
});

// --- UTILITY FUNCTIONS ---
async function sendMessage(text) {
    try {
        console.log(`🤖 Sending: "${text}"`);
        await client.sendMessage(MY_NUMBER, text);
        console.log(`✅ Message sent successfully`);
    } catch (error) {
        console.error(`❌ Failed to send message:`, error.message);
    }
}

function validateEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function validatePassword(password) {
    return password && password.length >= 6;
}

function getUserState() {
    return userStates.get(MY_NUMBER) || { state: STATES.IDLE };
}

function setUserState(state, data = {}) {
    userStates.set(MY_NUMBER, { state, ...data });
}

function clearUserState() {
    userStates.delete(MY_NUMBER);
}

// --- API FUNCTIONS ---
async function registerUser(name, email, password) {
    try {
        const payload = {
            name: name.trim(),
            email: email.trim(),
            password: password,
            phone_number: MY_NUMBER.split('@')[0]
        };
        
        console.log(`📝 Registering user:`, { name, email, phone: payload.phone_number });
        
        const response = await axios.post(`${API_ENDPOINT}/auth/register`, payload);
        console.log(`✅ Registration successful`);
        return { success: true, data: response.data };
    } catch (error) {
        console.error(`❌ Registration failed:`, error.response?.data || error.message);
        let errorMsg = "Hmm, something went wrong with the registration. ";
        
        if (error.response?.status === 400) {
            const detail = error.response.data?.detail || "";
            if (detail.includes("email")) {
                errorMsg = "It looks like this email is already registered! 📧 Do you want to try logging in instead?";
            } else if (detail.includes("phone")) {
                errorMsg = "This phone number is already registered! 📱 Would you like to login?";
            } else {
                errorMsg += detail;
            }
        } else {
            errorMsg += "Could you please try again in a moment?";
        }
        
        return { success: false, error: errorMsg };
    }
}

async function loginUser(password) {
    try {
        const payload = {
            phone_number: MY_NUMBER.split('@')[0],
            password: password
        };

        console.log(`🔐 Logging in user:`, { phone: payload.phone_number });

        const response = await axios.post(`${API_ENDPOINT}/auth/phone-login`, payload);
        bearerToken = response.data.tokens.access_token;
        isAuthenticated = true;

        // Generate a unique session ID for this conversation
        conversationSessionId = `whatsapp_${MY_NUMBER.split('@')[0]}_${Date.now()}`;

        console.log(`✅ Login successful, session: ${conversationSessionId}`);
        return { success: true, token: bearerToken };
    } catch (error) {
        console.error(`❌ Login failed:`, error.response?.data || error.message);
        return { success: false, error: "Hmm, that password doesn't seem right. Could you double-check it? 🔐" };
    }
}

async function sendToAI(userInput) {
    try {
        console.log(`🧠 Sending to AI: "${userInput}" (session: ${conversationSessionId})`);

        const payload = {
            user_message: userInput,
            session_id: conversationSessionId,
            file_ids: []
        };
        const headers = { Authorization: `Bearer ${bearerToken}` };

        const response = await axios.post(`${API_ENDPOINT}/enhanced_conversation/message`, payload, { headers });

        // Update session ID from response to maintain continuity
        if (response.data.session_id) {
            conversationSessionId = response.data.session_id;
        }

        console.log(`✅ AI response received (session: ${conversationSessionId})`);
        return { success: true, message: response.data.response || "I understand! How can I help you further?" };
    } catch (error) {
        console.error(`❌ AI request failed:`, error.response?.data || error.message);

        if (error.response?.status === 401) {
            bearerToken = null;
            isAuthenticated = false;
            conversationSessionId = null;
            return { success: false, error: "Oops! Your session expired. Let me help you log back in! 🔄" };
        }

        return { success: false, error: "I'm having a little trouble processing that right now. Could you try again? 🤔" };
    }
}

// --- CONVERSATIONAL HANDLERS ---
async function startRegistration() {
    setUserState(STATES.REGISTRATION_NAME);
    await sendMessage(
        "Great! Let's get you set up! 🎉\n\n" +
        "First, what's your name? (This will help me personalize our conversations)"
    );
}

async function handleRegistrationName(input) {
    const name = input.trim();
    
    if (!name || name.length < 2) {
        await sendMessage(
            "I need a bit more than that! 😅 Could you tell me your full name? " +
            "It should be at least 2 characters long."
        );
        return;
    }
    
    setUserState(STATES.REGISTRATION_EMAIL, { name });
    await sendMessage(
        `Nice to meet you, ${name}! 👋\n\n` +
        "Now, what's your email address? I'll use this for your account."
    );
}

async function handleRegistrationEmail(input) {
    const email = input.trim();
    const currentState = getUserState();
    
    if (!validateEmail(email)) {
        await sendMessage(
            "Hmm, that doesn't look like a valid email address. 📧\n\n" +
            "Could you try again? Something like: john@gmail.com"
        );
        return;
    }
    
    setUserState(STATES.REGISTRATION_PASSWORD, { 
        name: currentState.name,
        email: email 
    });
    
    await sendMessage(
        "Perfect! 📧 Email saved.\n\n" +
        "Last step: Create a password (at least 6 characters). " +
        "Make it something you'll remember! 🔐"
    );
}

async function handleRegistrationPassword(input) {
    const password = input.trim();
    const currentState = getUserState();
    
    if (!validatePassword(password)) {
        await sendMessage(
            "Your password needs to be at least 6 characters long for security! 🛡️\n\n" +
            "Please try again with a longer password."
        );
        return;
    }
    
    await sendMessage("🎯 Creating your account... just a moment!");
    
    const result = await registerUser(currentState.name, currentState.email, password);
    
    clearUserState();
    
    if (result.success) {
        await sendMessage(
            "🎉 Awesome! Your account is ready!\n\n" +
            "Let me log you in right away..."
        );
        
        // Auto-login after registration
        const loginResult = await loginUser(password);
        if (loginResult.success) {
            await sendMessage(
                `Welcome aboard, ${currentState.name}! ✨\n\n` +
                "I'm your AI Form Assistant! I can help you with:\n" +
                "📝 Creating and filling out forms\n" +
                "❓ Answering your questions\n" +
                "📊 Generating reports\n\n" +
                "What would you like to work on today? Just tell me in plain English! 😊"
            );
        } else {
            await sendMessage(
                "✅ Account created successfully!\n\n" +
                "Just say 'login' and I'll help you sign in!"
            );
        }
    } else {
        await sendMessage(`${result.error}\n\nWant to try something else?`);
    }
}

async function startLogin() {
    if (isAuthenticated) {
        await sendMessage("You're already logged in! 😊 What can I help you with?");
        return;
    }
    
    setUserState(STATES.LOGIN_PASSWORD);
    await sendMessage(
        "Welcome back! 👋\n\n" +
        "Please enter your password to continue:"
    );
}

async function handleLoginPassword(input) {
    const password = input.trim();
    
    await sendMessage("🔐 Checking your credentials...");
    
    const result = await loginUser(password);
    
    clearUserState();
    
    if (result.success) {
        await sendMessage(
            "🎉 Welcome back! Great to see you again!\n\n" +
            "I'm ready to help you with anything you need. What's on your mind today?"
        );
    } else {
        await sendMessage(
            `${result.error}\n\n` +
            "Want to try again? Just say 'login'. Or if you need a new account, say 'register'! 😊"
        );
    }
}

async function handleLogout() {
    bearerToken = null;
    isAuthenticated = false;
    conversationSessionId = null;
    clearUserState();

    await sendMessage(
        "👋 You've been logged out successfully!\n\n" +
        "Thanks for using AI Form Assistant! Come back anytime by saying 'login'."
    );
}

async function showHelp() {
    if (isAuthenticated) {
        await sendMessage(
            "🤖 *I'm here to help!*\n\n" +
            "Here's what I can do:\n" +
            "📝 Help you create and fill forms\n" +
            "❓ Answer questions about anything\n" +
            "📊 Generate reports and summaries\n" +
            "🚪 Type 'logout' if you want to sign out\n\n" +
            "*Just chat with me naturally!* Try things like:\n" +
            "• \"I need to create a patient form\"\n" +
            "• \"Show me my recent forms\"\n" +
            "• \"Help me with a report\"\n\n" +
            "What would you like to do? 😊"
        );
    } else {
        await sendMessage(
            "🤖 *Hi! I'm your AI Form Assistant!*\n\n" +
            "I can help you with forms, questions, and reports, but first you'll need an account.\n\n" +
            "✨ *Getting started is easy:*\n" +
            "• Say 'register' to create a new account\n" +
            "• Say 'login' if you already have one\n\n" +
            "I'll guide you through everything step by step! 😊"
        );
    }
}

// --- SMART MESSAGE PROCESSOR ---
async function processMessage(messageBody) {
    if (isProcessing) {
        console.log("⏸️ Already processing a message, ignoring...");
        return;
    }
    
    isProcessing = true;
    
    try {
        const input = messageBody.trim();
        const lowerInput = input.toLowerCase();
        const currentState = getUserState();
        
        console.log(`🔥 Processing: "${input}"`);
        console.log(`🔍 Current state: ${currentState.state}, Authenticated: ${isAuthenticated}`);
        
        // Handle state-based conversations first
        if (currentState.state === STATES.REGISTRATION_NAME) {
            await handleRegistrationName(input);
            return;
        }
        
        if (currentState.state === STATES.REGISTRATION_EMAIL) {
            await handleRegistrationEmail(input);
            return;
        }
        
        if (currentState.state === STATES.REGISTRATION_PASSWORD) {
            await handleRegistrationPassword(input);
            return;
        }
        
        if (currentState.state === STATES.LOGIN_PASSWORD) {
            await handleLoginPassword(input);
            return;
        }
        
        // Handle natural language commands
        if (lowerInput.includes('register') || lowerInput.includes('sign up') || lowerInput.includes('create account')) {
            if (isAuthenticated) {
                await sendMessage("You're already registered and logged in! 😊 What can I help you with?");
            } else {
                await startRegistration();
            }
        }
        else if (lowerInput.includes('login') || lowerInput.includes('sign in') || lowerInput.includes('log in')) {
            await startLogin();
        }
        else if (lowerInput.includes('logout') || lowerInput.includes('sign out') || lowerInput.includes('log out')) {
            if (isAuthenticated) {
                await handleLogout();
            } else {
                await sendMessage("You're not logged in yet! 😅 Say 'login' to get started.");
            }
        }
        else if (lowerInput.includes('help') || lowerInput.includes('what can you do') || lowerInput === '?') {
            await showHelp();
        }
        else if (lowerInput === 'status' || lowerInput === 'debug') {
            // Debug command
            await sendMessage(
                `🔍 *Debug Info*\n\n` +
                `Status: ${isAuthenticated ? '🟢 Logged in' : '🔴 Not logged in'}\n` +
                `State: ${currentState.state}\n` +
                `Session: ${conversationSessionId || '❌ None'}\n` +
                `Token: ${bearerToken ? '✅ Present' : '❌ None'}`
            );
        }
        else if (lowerInput.includes('cancel') || lowerInput.includes('stop') || lowerInput.includes('nevermind')) {
            clearUserState();
            await sendMessage("No problem! 😊 Canceled. What else can I help you with?");
        }
        else if (isAuthenticated) {
            // Handle regular AI conversation
            await sendMessage("💭 Let me think about that...");
            
            const result = await sendToAI(input);
            
            if (result.success) {
                await sendMessage(result.message);
            } else {
                await sendMessage(result.error);
                if (!isAuthenticated) {
                    await sendMessage("Let's get you logged in again! Just say 'login'. 😊");
                }
            }
        }
        else {
            // Not authenticated - friendly welcome
            const greetings = ['hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening'];
            const isGreeting = greetings.some(greeting => lowerInput.includes(greeting));
            
            if (isGreeting) {
                await sendMessage(
                    "Hello there! 👋 Welcome to AI Form Assistant!\n\n" +
                    "I'm here to help you with forms, questions, and reports. " +
                    "To get started, I'll need you to either:\n\n" +
                    "✨ Say 'register' to create a new account\n" +
                    "🔑 Say 'login' if you already have one\n\n" +
                    "I'll guide you through everything! What would you like to do?"
                );
            } else {
                await sendMessage(
                    "I'd love to help you with that! 😊\n\n" +
                    "But first, I'll need you to get set up:\n\n" +
                    "✨ Say 'register' for a new account\n" +
                    "🔑 Say 'login' if you have one already\n\n" +
                    "It'll just take a moment!"
                );
            }
        }
    } catch (error) {
        console.error("❌ Error processing message:", error);
        clearUserState();
        await sendMessage(
            "Oops! I ran into a little hiccup. 😅\n\n" +
            "Could you try that again? Or say 'help' if you need assistance!"
        );
    } finally {
        isProcessing = false;
    }
}

// --- WHATSAPP EVENT HANDLERS ---
client.on('qr', (qr) => {
    console.log("📱 Scan this QR code with WhatsApp:");
    console.log("--------------------------------------------------");
    qrcode.generate(qr, { small: true });
    console.log("--------------------------------------------------");
});

client.on('ready', () => {
    console.log('✅ WhatsApp client is ready!');
    console.log(`📞 Bot number: ${MY_NUMBER}`);
    console.log(`🌐 API endpoint: ${API_ENDPOINT}`);
    console.log('📄 Waiting for messages...');
});

client.on('disconnected', (reason) => {
    console.log('⚠️ WhatsApp disconnected:', reason);
    // Reset state on disconnect
    bearerToken = null;
    isAuthenticated = false;
    conversationSessionId = null;
    isProcessing = false;
    userStates.clear();
});

client.on('auth_failure', (msg) => {
    console.error('❌ WhatsApp auth failed:', msg);
});

// --- MAIN MESSAGE HANDLER ---
client.on('message', async (message) => {
    try {
        // Only handle messages from our configured number
        if (message.from !== MY_NUMBER) {
            return;
        }
        
        // Skip messages from the bot itself
        if (message.fromMe) {
            return;
        }
        
        console.log(`👤 Received from user: "${message.body}"`);
        
        // Process the message
        await processMessage(message.body);
        
    } catch (error) {
        console.error("❌ Message handler error:", error);
    }
});

// --- STARTUP ---
console.log("🚀 Starting Conversational WhatsApp AI Bot...");
console.log(`📱 Target number: ${MY_NUMBER}`);
console.log(`🌐 API endpoint: ${API_ENDPOINT}`);

// Handle graceful shutdown
process.on('SIGINT', async () => {
    console.log('\n🛑 Shutting down...');
    try {
        await client.destroy();
    } catch (error) {
        console.error('Error during shutdown:', error);
    }
    process.exit(0);
});

// Start the client
client.initialize().catch(error => {
    console.error("❌ Failed to initialize:", error);
    process.exit(1);
});