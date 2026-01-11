import React, { useState, useRef, useEffect } from 'react';
import { PaperAirplaneIcon, PaperClipIcon, XMarkIcon } from '@heroicons/react/24/solid';
import { motion } from 'framer-motion';

interface ChatInputProps {
  onSendMessage: (message: string, files?: File[]) => void;
  isLoading?: boolean;
  placeholder?: string;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  onSendMessage,
  isLoading = false,
  placeholder = 'Message FlowForm AI...',
}) => {
  const [message, setMessage] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [message]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() || files.length > 0) {
      onSendMessage(message, files.length > 0 ? files : undefined);
      setMessage('');
      setFiles([]);
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFiles(Array.from(e.target.files));
    }
  };

  const removeFile = (index: number) => {
    setFiles(files.filter((_, i) => i !== index));
  };

  return (
    <div className="border-t border-border bg-background py-4 px-4">
      <div className="max-w-3xl mx-auto">
        <form onSubmit={handleSubmit}>
          {/* File Preview */}
          {files.length > 0 && (
            <div className="mb-3 flex flex-wrap gap-2">
              {files.map((file, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="flex items-center gap-2 bg-muted rounded-full px-3 py-1.5 text-sm"
                >
                  <PaperClipIcon className="w-4 h-4 text-muted-foreground" />
                  <span className="text-foreground truncate max-w-[150px]">{file.name}</span>
                  <button
                    type="button"
                    onClick={() => removeFile(index)}
                    className="text-muted-foreground hover:text-foreground"
                  >
                    <XMarkIcon className="w-4 h-4" />
                  </button>
                </motion.div>
              ))}
            </div>
          )}

          {/* Gemini-style Input Container */}
          <div className="relative bg-muted rounded-3xl border border-border/50 shadow-sm focus-within:shadow-md focus-within:border-primary/30 transition-all">
            <textarea
              ref={textareaRef}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={placeholder}
              disabled={isLoading}
              rows={1}
              className="
                w-full resize-none bg-transparent rounded-3xl
                px-5 py-4 pr-24 text-foreground
                placeholder:text-muted-foreground
                focus:outline-none
                disabled:opacity-50 disabled:cursor-not-allowed
                max-h-[200px] overflow-y-auto
              "
              style={{ minHeight: '56px' }}
            />

            {/* Actions Container */}
            <div className="absolute right-2 bottom-2 flex items-center gap-1">
              {/* File Upload Button */}
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={isLoading}
                className="
                  p-2 rounded-full text-muted-foreground
                  hover:text-foreground hover:bg-muted-foreground/10
                  transition-colors disabled:opacity-50
                "
                title="Attach files"
              >
                <PaperClipIcon className="w-5 h-5" />
              </button>
              <input
                ref={fileInputRef}
                type="file"
                onChange={handleFileChange}
                multiple
                className="hidden"
                accept="image/*,.pdf,.txt,.doc,.docx,.mp3,.wav,.m4a"
              />

              {/* Send Button */}
              <motion.button
                type="submit"
                disabled={isLoading || (!message.trim() && files.length === 0)}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="
                  p-2 rounded-full bg-primary text-primary-foreground
                  disabled:opacity-30 disabled:cursor-not-allowed
                  transition-all
                "
              >
                {isLoading ? (
                  <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                ) : (
                  <PaperAirplaneIcon className="w-5 h-5" />
                )}
              </motion.button>
            </div>
          </div>

          {/* Helper Text */}
          <div className="mt-2 text-xs text-muted-foreground text-center">
            <span className="opacity-70">Press Enter to send, Shift+Enter for new line</span>
          </div>
        </form>
      </div>
    </div>
  );
};
