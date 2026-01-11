import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { PlusIcon, ChatBubbleLeftIcon, TrashIcon, XMarkIcon } from '@heroicons/react/24/outline';
import { Button } from '../ui/Button';

interface Conversation {
  id: string;
  title: string;
  lastMessage?: string;
  timestamp?: Date;
}

interface ChatSidebarProps {
  conversations: Conversation[];
  activeConversationId?: string;
  onSelectConversation: (id: string) => void;
  onNewConversation: () => void;
  onDeleteConversation?: (id: string) => void;
  isOpen?: boolean;
  onToggle?: () => void;
}

export const ChatSidebar: React.FC<ChatSidebarProps> = ({
  conversations,
  activeConversationId,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
  isOpen = true,
  onToggle,
}) => {
  const formatTime = (date?: Date) => {
    if (!date) return '';
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const hours = Math.floor(diff / (1000 * 60 * 60));

    if (hours < 1) return 'Just now';
    if (hours < 24) return `${hours}h ago`;
    return date.toLocaleDateString();
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ width: 0, opacity: 0 }}
          animate={{ width: 280, opacity: 1 }}
          exit={{ width: 0, opacity: 0 }}
          transition={{ duration: 0.2 }}
          className="h-full bg-muted/30 border-r border-border flex flex-col overflow-hidden"
        >
          {/* Header */}
          <div className="p-3 border-b border-border flex items-center justify-between">
            <Button
              variant="default"
              className="flex-1 rounded-xl h-10 text-sm"
              onClick={onNewConversation}
            >
              <PlusIcon className="w-4 h-4 mr-2" />
              New Chat
            </Button>
            {onToggle && (
              <button
                onClick={onToggle}
                className="ml-2 p-2 hover:bg-muted rounded-lg transition-colors"
              >
                <XMarkIcon className="w-5 h-5 text-muted-foreground" />
              </button>
            )}
          </div>

          {/* Conversations List */}
          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {conversations.length === 0 ? (
              <div className="text-center py-12 px-4">
                <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center mx-auto mb-3">
                  <ChatBubbleLeftIcon className="w-6 h-6 text-muted-foreground" />
                </div>
                <p className="text-sm text-muted-foreground">No conversations yet</p>
                <p className="text-xs text-muted-foreground/70 mt-1">Start a new chat</p>
              </div>
            ) : (
              conversations.map((conversation) => (
                <motion.div
                  key={conversation.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  className={`
                    group relative p-3 rounded-xl cursor-pointer transition-all
                    ${activeConversationId === conversation.id
                      ? 'bg-primary/10 border border-primary/20'
                      : 'hover:bg-muted'
                    }
                  `}
                  onClick={() => onSelectConversation(conversation.id)}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <h4 className="text-sm font-medium text-foreground truncate">
                        {conversation.title}
                      </h4>
                      {conversation.lastMessage && (
                        <p className="text-xs text-muted-foreground truncate mt-0.5">
                          {conversation.lastMessage}
                        </p>
                      )}
                      {conversation.timestamp && (
                        <span className="text-xs text-muted-foreground/70 mt-1 block">
                          {formatTime(conversation.timestamp)}
                        </span>
                      )}
                    </div>
                    {onDeleteConversation && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onDeleteConversation(conversation.id);
                        }}
                        className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg hover:bg-destructive/10 text-destructive transition-all"
                        title="Delete conversation"
                      >
                        <TrashIcon className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </motion.div>
              ))
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
