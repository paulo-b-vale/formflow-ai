import { useState, useEffect, useRef, FC } from 'react';
import { v4 as uuidv4 } from 'uuid';
import withAuth from '../withAuth';
import { MessageBubble } from './MessageBubble';
import { ChatInput } from './ChatInput';
import { ChatSidebar } from './ChatSidebar';
import { ThemeToggle } from '../ui/ThemeToggle';
import api from '../../lib/api';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  sessionId: string;
  lastMessage?: string;
  timestamp: Date;
}

const EnhancedChatInterface: FC = () => {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | undefined>(undefined);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Initialize with first conversation
  useEffect(() => {
    createNewConversation();
  }, []);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    scrollToBottom();
  }, [conversations, activeConversationId]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const createNewConversation = () => {
    const newConversation: Conversation = {
      id: uuidv4(),
      title: 'New Conversation',
      messages: [
        {
          id: uuidv4(),
          role: 'assistant',
          content:
            "Hello! I am your AI assistant. How can I help you fill out a form today? For example, you can ask for a 'construction form', 'permit application', or describe what form you need.",
          timestamp: new Date(),
        },
      ],
      sessionId: `session_${Date.now()}`,
      lastMessage: 'Hello! I am your AI assistant...',
      timestamp: new Date(),
    };

    setConversations((prev) => [newConversation, ...prev]);
    setActiveConversationId(newConversation.id);
  };

  const getActiveConversation = (): Conversation | undefined => {
    return conversations.find((c) => c.id === activeConversationId);
  };

  const updateConversation = (conversationId: string, updates: Partial<Conversation>) => {
    setConversations((prev) =>
      prev.map((conv) =>
        conv.id === conversationId ? { ...conv, ...updates, timestamp: new Date() } : conv
      )
    );
  };

  const handleSendMessage = async (messageText: string, files?: File[]) => {
    if (isLoading || !messageText.trim()) return;

    const activeConv = getActiveConversation();
    if (!activeConv) return;

    // Add user message
    const userMessage: Message = {
      id: uuidv4(),
      role: 'user',
      content: messageText,
      timestamp: new Date(),
    };

    const updatedMessages = [...activeConv.messages, userMessage];
    updateConversation(activeConv.id, {
      messages: updatedMessages,
      lastMessage: messageText.slice(0, 50),
      title: activeConv.messages.length === 1 ? messageText.slice(0, 30) : activeConv.title,
    });

    setIsLoading(true);

    try {
      // Handle file uploads if present
      let fileIds: string[] = [];
      if (files && files.length > 0) {
        const formData = new FormData();
        files.forEach((file) => {
          formData.append('files', file);
        });

        // Upload files and get file IDs
        try {
          const uploadResponse = await api.post('/files/chat/upload', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
          });
          fileIds = uploadResponse.data.files?.map((f: any) => f.file_id) || [];
          console.log('Files uploaded successfully:', fileIds);
        } catch (uploadError) {
          console.error('File upload failed:', uploadError);
        }
      }

      // Send message to backend with file IDs
      const response = await api.post('/enhanced_conversation/message', {
        session_id: activeConv.sessionId,
        user_message: messageText,
        file_ids: fileIds.length > 0 ? fileIds : undefined,
      });

      // Add assistant response
      const assistantMessage: Message = {
        id: uuidv4(),
        role: 'assistant',
        content: response.data.response,
        timestamp: new Date(),
      };

      const finalMessages = [...updatedMessages, assistantMessage];
      updateConversation(activeConv.id, {
        messages: finalMessages,
        sessionId: response.data.session_id,
        lastMessage: response.data.response.slice(0, 50),
      });
    } catch (error) {
      console.error('Failed to send message:', error);

      const errorMessage: Message = {
        id: uuidv4(),
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date(),
      };

      updateConversation(activeConv.id, {
        messages: [...updatedMessages, errorMessage],
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteConversation = (conversationId: string) => {
    setConversations((prev) => prev.filter((c) => c.id !== conversationId));

    if (activeConversationId === conversationId) {
      const remaining = conversations.filter((c) => c.id !== conversationId);
      if (remaining.length > 0) {
        setActiveConversationId(remaining[0].id);
      } else {
        createNewConversation();
      }
    }
  };

  const activeConversation = getActiveConversation();

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-gray-950">
      {/* Sidebar */}
      <ChatSidebar
        conversations={conversations}
        activeConversationId={activeConversationId}
        onSelectConversation={setActiveConversationId}
        onNewConversation={createNewConversation}
        onDeleteConversation={handleDeleteConversation}
      />

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                {activeConversation?.title || 'AI Form Assistant'}
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                Intelligent form filling assistance powered by AI
              </p>
            </div>
            <ThemeToggle />
          </div>
        </div>

        {/* Messages Container */}
        <div className="flex-1 overflow-y-auto bg-gray-50 dark:bg-gray-950 p-6">
          <div className="max-w-4xl mx-auto space-y-4">
            {activeConversation?.messages.map((message, index) => (
              <MessageBubble
                key={message.id}
                message={message}
                isLast={index === activeConversation.messages.length - 1}
              />
            ))}
            {isLoading && (
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-600 to-blue-600 flex items-center justify-center text-white font-semibold">
                  AI
                </div>
                <div className="flex gap-1">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-100" />
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-200" />
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Chat Input */}
        <ChatInput onSendMessage={handleSendMessage} isLoading={isLoading} />
      </div>
    </div>
  );
};

export default withAuth(EnhancedChatInterface);