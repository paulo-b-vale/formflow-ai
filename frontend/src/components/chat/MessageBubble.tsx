import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { ClipboardIcon, CheckIcon } from '@heroicons/react/24/outline';
import { MessageMarkdown } from './MessageMarkdown';

interface MessageBubbleProps {
  message: {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    timestamp?: Date;
  };
  isLast?: boolean;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message, isLast = false }) => {
  const [isCopied, setIsCopied] = useState(false);
  const isUser = message.role === 'user';

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content);
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 2000);
  };

  const formatTime = (date?: Date) => {
    if (!date) return '';
    return new Intl.DateTimeFormat('en-US', {
      hour: 'numeric',
      minute: 'numeric',
      hour12: true,
    }).format(date);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={`flex gap-4 py-6 group ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
    >
      {/* Avatar */}
      {isUser ? (
        <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-primary-foreground text-sm font-medium flex-shrink-0">
          U
        </div>
      ) : (
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 via-pink-500 to-orange-400 flex items-center justify-center flex-shrink-0">
          <svg className="w-5 h-5 text-white" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2L13.09 8.26L19 9.27L13.18 14.14L14.18 20.02L12 17.77L9.82 20.02L10.82 14.14L5 9.27L10.91 8.26L12 2Z" />
          </svg>
        </div>
      )}

      {/* Message Content */}
      <div className={`flex-1 min-w-0 ${isUser ? 'flex justify-end' : ''}`}>
        <div
          className={`
            ${isUser
              ? 'bg-primary text-primary-foreground rounded-3xl rounded-tr-lg px-5 py-3 max-w-[85%] inline-block'
              : 'text-foreground max-w-full'
            }
          `}
        >
          {isUser ? (
            <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="text-sm leading-relaxed prose prose-sm dark:prose-invert max-w-none">
              <MessageMarkdown content={message.content} />
            </div>
          )}
        </div>

        {/* Actions row */}
        <div className={`flex items-center gap-2 mt-2 ${isUser ? 'justify-end' : 'justify-start'}`}>
          {message.timestamp && (
            <span className="text-xs text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity">
              {formatTime(message.timestamp)}
            </span>
          )}

          {!isUser && (
            <button
              onClick={handleCopy}
              className="p-1.5 rounded-md opacity-0 group-hover:opacity-100 hover:bg-muted transition-all"
              title="Copy message"
            >
              {isCopied ? (
                <CheckIcon className="w-4 h-4 text-green-500" />
              ) : (
                <ClipboardIcon className="w-4 h-4 text-muted-foreground" />
              )}
            </button>
          )}
        </div>
      </div>
    </motion.div>
  );
};