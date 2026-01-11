import React from 'react';

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

  if (!isOpen) return null;

  return (
    <div className="w-72 h-full glass-sidebar flex flex-col animate-fade-in">
      {/* Header */}
      <div className="p-4 border-b border-border/50">
        <button
          onClick={onNewConversation}
          className="w-full btn-primary py-3 rounded-xl flex items-center justify-center gap-2 text-sm font-medium"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          New Chat
        </button>

        {onToggle && (
          <button
            onClick={onToggle}
            className="absolute top-4 right-4 p-2 hover:bg-muted rounded-lg transition-colors"
          >
            <svg className="w-5 h-5 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>

      {/* Conversations List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2 scrollbar-thin">
        {conversations.length === 0 ? (
          <div className="text-center py-12 px-4">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-slate-500/20 to-blue-500/20 flex items-center justify-center mx-auto mb-4">
              <svg className="w-7 h-7 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            </div>
            <p className="text-sm font-medium text-muted-foreground">No conversations yet</p>
            <p className="text-xs text-muted-foreground/70 mt-1">Start a new chat to begin</p>
          </div>
        ) : (
          conversations.map((conversation) => (
            <div
              key={conversation.id}
              className={`
                group relative p-3 rounded-xl cursor-pointer transition-all duration-200
                ${activeConversationId === conversation.id
                  ? 'bg-gradient-to-r from-blue-500/10 to-teal-500/10 border border-blue-500/20 shadow-sm'
                  : 'hover:bg-muted/50'
                }
              `}
              onClick={() => onSelectConversation(conversation.id)}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-start gap-3 flex-1 min-w-0">
                  <div className={`
                    w-8 h-8 rounded-lg flex-shrink-0 flex items-center justify-center
                    ${activeConversationId === conversation.id
                      ? 'bg-gradient-to-br from-blue-500 to-teal-500 text-white'
                      : 'bg-muted text-muted-foreground'
                    }
                  `}>
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                    </svg>
                  </div>
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
                      <span className="text-xs text-muted-foreground/60 mt-1 block">
                        {formatTime(conversation.timestamp)}
                      </span>
                    )}
                  </div>
                </div>

                {onDeleteConversation && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteConversation(conversation.id);
                    }}
                    className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg hover:bg-red-500/10 text-red-500 transition-all"
                    title="Delete conversation"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-border/50">
        <div className="text-xs text-muted-foreground/60 text-center">
          FlowForm AI Assistant
        </div>
      </div>
    </div>
  );
};
