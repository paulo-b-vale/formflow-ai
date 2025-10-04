import React from 'react';
import { motion } from 'framer-motion';
import { PlusIcon, ChatBubbleLeftIcon, TrashIcon } from '@heroicons/react/24/outline';
import { Button } from '../ui';

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
}

export const ChatSidebar: React.FC<ChatSidebarProps> = ({
  conversations,
  activeConversationId,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
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
    <div className="w-80 h-full bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700 flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <Button
          variant="primary"
          className="w-full"
          onClick={onNewConversation}
        >
          <PlusIcon className="w-5 h-5 mr-2" />
          New Conversation
        </Button>
      </div>

      {/* Conversations List */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {conversations.length === 0 ? (
          <div className="text-center py-12 text-gray-500 dark:text-gray-400">
            <ChatBubbleLeftIcon className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p className="text-sm">No conversations yet</p>
            <p className="text-xs mt-1">Start a new chat to begin</p>
          </div>
        ) : (
          conversations.map((conversation) => (
            <motion.div
              key={conversation.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              className={`
                group relative p-3 rounded-lg cursor-pointer transition-all
                ${
                  activeConversationId === conversation.id
                    ? 'bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800'
                    : 'hover:bg-gray-100 dark:hover:bg-gray-800'
                }
              `}
              onClick={() => onSelectConversation(conversation.id)}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                    {conversation.title}
                  </h4>
                  {conversation.lastMessage && (
                    <p className="text-xs text-gray-500 dark:text-gray-400 truncate mt-1">
                      {conversation.lastMessage}
                    </p>
                  )}
                </div>
                {onDeleteConversation && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteConversation(conversation.id);
                    }}
                    className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-100 dark:hover:bg-red-900/20 text-red-600 dark:text-red-400 transition-opacity"
                    title="Delete conversation"
                  >
                    <TrashIcon className="w-4 h-4" />
                  </button>
                )}
              </div>
              {conversation.timestamp && (
                <span className="text-xs text-gray-400 dark:text-gray-500 mt-1 block">
                  {formatTime(conversation.timestamp)}
                </span>
              )}
            </motion.div>
          ))
        )}
      </div>
    </div>
  );
};
