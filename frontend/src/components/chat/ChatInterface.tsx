import { useState, useEffect, FC } from 'react';
import withAuth from '../withAuth';
import MessageWindow from './MessageWindow';
import ChatInput from './ChatInput';
import api from '../../lib/api';

// Define the structure of a message
interface ChatMessage {
  text: string;
  sender: 'user' | 'bot';
}

const ChatInterface: FC = () => {
  // State is managed here, in the parent component
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Add a welcome message on component mount
  useEffect(() => {
    setMessages([{
      sender: 'bot',
      text: "Hello! I am your AI assistant. How can I help you fill out a form today? For example, you can ask for a 'construction form', 'permit application', or describe what form you need."
    }]);
    // Initialize session ID
    setSessionId(`session_${Date.now()}`);
  }, []);

  const handleSend = async (message: string) => {
    if (isLoading || !message.trim() || !sessionId) return;

    const userMessage: ChatMessage = { text: message, sender: 'user' };
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      // The frontend now correctly calls the enhanced conversation endpoint
      const response = await api.post('/enhanced_conversation/message', {
        session_id: sessionId,
        user_message: message, // The backend expects 'user_message' in the body
      });
      
      const botMessage: ChatMessage = {
        text: response.data.response, // The backend sends 'response' in the response
        sender: 'bot',
      };
      
      setMessages(prev => [...prev, botMessage]);
      setSessionId(response.data.session_id);

    } catch (error) {
      console.error('Failed to send message:', error);
      const errorMessage: ChatMessage = {
        text: 'Sorry, I encountered an error. Please try again.',
        sender: 'bot',
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[80vh] bg-white rounded shadow-lg">
      <h1 className="text-2xl font-bold p-4 border-b text-center">AI Form Assistant</h1>
      {/* The MessageWindow component receives the messages and loading state as props */}
      <MessageWindow messages={messages} isLoading={isLoading} />
      {/* The ChatInput component receives the onSend handler and loading state as props */}
      <ChatInput onSend={handleSend} isLoading={isLoading} />
    </div>
  );
};

export default withAuth(ChatInterface);