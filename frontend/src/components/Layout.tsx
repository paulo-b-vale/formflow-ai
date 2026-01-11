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
      <nav className="bg-primary text-primary-foreground p-4">
        <div className="container mx-auto flex justify-between items-center">
          <Link href="/" className="font-bold text-xl">
            FlowForm
          </Link>
          <div className="flex items-center space-x-4">
            {user ? (
              <>
                <span className="text-primary-foreground/80">Welcome, {user.name}!</span>

                {user.role === 'admin' ? (
                  <Link href="/admin" className="hover:text-primary-foreground/80 font-semibold">Admin</Link>
                ) : (
                  <>
                    <Link href="/dashboard" className="hover:text-primary-foreground/80">Dashboard</Link>
                    <Link href="/chat" className="hover:text-primary-foreground/80 font-semibold">Chat</Link>
                    <Link href="/responses" className="hover:text-primary-foreground/80">My Responses</Link>
                  </>
                )}

                <button onClick={logout} className="bg-destructive hover:bg-destructive/90 text-destructive-foreground px-3 py-1 rounded text-sm">Logout</button>
              </>
            ) : (
              <>
                <Link href="/login" className="hover:text-primary-foreground/80">Login</Link>
                <Link href="/register" className="hover:text-primary-foreground/80">Register</Link>
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