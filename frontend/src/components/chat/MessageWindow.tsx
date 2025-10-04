import { FC } from 'react';

// Define the structure of a message
interface ChatMessage {
  text: string;
  sender: 'user' | 'bot';
}

interface MessageWindowProps {
  messages: ChatMessage[];
  isLoading: boolean;
}

const MessageWindow: FC<MessageWindowProps> = ({ messages, isLoading }) => {
  return (
    <div className="flex flex-col h-[70vh] p-4 overflow-y-auto">
      {messages.map((msg, index) => (
        <div 
          key={index} 
          className={`mb-4 p-3 rounded-lg max-w-[80%] ${
            msg.sender === 'user' 
              ? 'bg-blue-500 text-white ml-auto' 
              : 'bg-gray-200 text-gray-800'
          }`}
        >
          {msg.text}
        </div>
      ))}
      {isLoading && (
        <div className="mb-4 p-3 rounded-lg bg-gray-200 text-gray-800">
          Thinking...
        </div>
      )}
    </div>
  );
};

export default MessageWindow;