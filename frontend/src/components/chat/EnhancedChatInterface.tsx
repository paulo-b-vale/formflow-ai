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
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    createNewConversation();
  }, []);

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
            "Hello! I'm your AI form assistant. I can help you create, fill out, or understand forms. What would you like to work on today?",
          timestamp: new Date(),
        },
      ],
      sessionId: `session_${Date.now()}`,
      lastMessage: 'Hello! I\'m your AI form assistant...',
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
      let fileIds: string[] = [];
      if (files && files.length > 0) {
        const formData = new FormData();
        files.forEach((file) => {
          formData.append('files', file);
        });

        try {
          const uploadResponse = await api.post('/files/chat/upload', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
          });
          fileIds = uploadResponse.data.files?.map((f: any) => f.file_id) || [];
        } catch (uploadError) {
          console.error('File upload failed:', uploadError);
        }
      }

      const response = await api.post('/enhanced_conversation/message', {
        session_id: activeConv.sessionId,
        user_message: messageText,
        file_ids: fileIds.length > 0 ? fileIds : undefined,
      });

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
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <ChatSidebar
        conversations={conversations}
        activeConversationId={activeConversationId}
        onSelectConversation={setActiveConversationId}
        onNewConversation={createNewConversation}
        onDeleteConversation={handleDeleteConversation}
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
      />

      {/* Main Chat Area - Gemini Style */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div className="h-16 border-b border-border flex items-center justify-between px-6 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
          <div className="flex items-center gap-3">
            {!sidebarOpen && (
              <button
                onClick={() => setSidebarOpen(true)}
                className="p-2 hover:bg-muted rounded-lg transition-colors"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              </button>
            )}
            <div className="flex items-center gap-2">
              {/* Gemini-style sparkle icon */}
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-slate-600 via-blue-500 to-teal-500 flex items-center justify-center">
                <svg className="w-5 h-5 text-white" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 2L13.09 8.26L19 9.27L13.18 14.14L14.18 20.02L12 17.77L9.82 20.02L10.82 14.14L5 9.27L10.91 8.26L12 2Z" />
                </svg>
              </div>
              <span className="font-semibold text-lg">FlowForm AI</span>
            </div>
          </div>
          <ThemeToggle />
        </div>

        {/* Messages Container - Centered like Gemini */}
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-3xl mx-auto py-8 px-4">
            {activeConversation?.messages.map((message, index) => (
              <MessageBubble
                key={message.id}
                message={message}
                isLast={index === activeConversation.messages.length - 1}
              />
            ))}

            {/* Loading indicator - Gemini style */}
            {isLoading && (
              <div className="flex gap-4 py-6">
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-slate-600 via-blue-500 to-teal-500 flex items-center justify-center flex-shrink-0">
                  <svg className="w-5 h-5 text-white" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 2L13.09 8.26L19 9.27L13.18 14.14L14.18 20.02L12 17.77L9.82 20.02L10.82 14.14L5 9.27L10.91 8.26L12 2Z" />
                  </svg>
                </div>
                <div className="flex items-center gap-1.5 pt-2">
                  <div className="w-2 h-2 bg-muted-foreground/40 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-2 h-2 bg-muted-foreground/40 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-2 h-2 bg-muted-foreground/40 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Chat Input - Centered at bottom */}
        <ChatInput onSendMessage={handleSendMessage} isLoading={isLoading} />
      </div>
    </div>
  );
};

export default withAuth(EnhancedChatInterface);