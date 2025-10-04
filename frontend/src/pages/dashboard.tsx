import withAuth from '@/components/withAuth';
import { useAuth } from '@/hooks/useAuth';
import Link from 'next/link';

function Dashboard() {
  const { user } = useAuth();
  return (
    <div>
      <h1 className="text-3xl font-bold">User Dashboard</h1>
      <p className="mt-2 text-lg">Welcome back, {user?.name}!</p>
      <div className="mt-6 bg-white p-6 rounded-lg shadow-md">
        <h2 className="text-xl font-semibold">Start a Conversation</h2>
        <p className="mt-2">Begin filling out a form or ask a question by starting a new chat with the AI assistant.</p>
        <Link href="/chat" className="mt-4 inline-block bg-blue-500 text-white font-bold py-2 px-4 rounded hover:bg-blue-600 transition-colors">
          Go to Chat
        </Link>
      </div>
    </div>
  );
}

export default withAuth(Dashboard);