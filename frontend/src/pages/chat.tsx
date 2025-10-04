import withAuth from '@/components/withAuth';
import ChatInterface from '@/components/chat/ChatInterface';

function ChatPage() {
  return (
    <div className="container mx-auto p-4">
      <h1 className="text-3xl font-bold mb-4 text-center">Conversation with AI Assistant</h1>
      {/* The ChatInterface component contains all the chat functionality */}
      <ChatInterface />
    </div>
  );
}

// Protect this page so only logged-in users can access it
export default withAuth(ChatPage);
