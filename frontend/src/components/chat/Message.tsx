import { FC } from 'react';

interface MessageProps {
  text: string;
  sender: 'user' | 'bot';
}

const Message: FC<MessageProps> = ({ text, sender }) => {
  const isUser = sender === 'user';
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-md lg:max-w-2xl px-4 py-2 rounded-lg ${
          isUser ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-800'
        }`}
      >
        <p style={{ whiteSpace: 'pre-wrap' }}>{text}</p>
      </div>
    </div>
  );
};

export default Message;