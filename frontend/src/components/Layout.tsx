import Link from 'next/link';
import { useAuth } from '@/hooks/useAuth';
import { ReactNode } from 'react';

interface LayoutProps {
  children: ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen flex flex-col">
      <nav className="bg-gray-800 text-white p-4">
        <div className="container mx-auto flex justify-between items-center">
          <Link href="/" className="font-bold text-xl">
            AI Form Assistant
          </Link>
          <div className="flex items-center space-x-4">
            {user ? (
              <>
                <span className="text-gray-300">Welcome, {user.name}!</span>
                
                {user.role === 'admin' ? (
                  <Link href="/admin" className="hover:text-gray-300 font-semibold">Admin Dashboard</Link>
                ) : (
                  <>
                    <Link href="/dashboard" className="hover:text-gray-300">Dashboard</Link>
                    <Link href="/chat" className="hover:text-gray-300 font-semibold">Chat</Link>
                    <Link href="/responses" className="hover:text-gray-300">My Responses</Link>
                  </>
                )}
                
                <button onClick={logout} className="bg-red-500 hover:bg-red-600 px-3 py-1 rounded">Logout</button>
              </>
            ) : (
              <>
                <Link href="/login" className="hover:text-gray-300">Login</Link>
                <Link href="/register" className="hover:text-gray-300">Register</Link>
              </>
            )}
          </div>
        </div>
      </nav>
      <main className="flex-grow container mx-auto p-4">
        {children}
      </main>
    </div>
  );
}