import { useAuth } from '@/hooks/useAuth';
import { useRouter } from 'next/router';
import { useEffect, ComponentType, useState } from 'react';

const withAdminAuth = <P extends object>(Component: ComponentType<P>) => {
  const AdminAuthComponent = (props: P) => {
    const { user, loading } = useAuth();
    const router = useRouter();
    const [isAuthorized, setIsAuthorized] = useState(false);

    useEffect(() => {
      // Wait for auth to finish loading
      if (loading) return;

      // If no user or not admin, redirect immediately
      if (!user || user.role !== 'admin') {
        router.replace('/login');
        return;
      }

      // User is admin, allow access
      setIsAuthorized(true);
    }, [user, loading, router]);

    // Show loading while checking auth
    if (loading || !isAuthorized) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-background">
          <div className="flex flex-col items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-slate-600 via-blue-500 to-teal-500 flex items-center justify-center animate-pulse">
              <svg className="w-6 h-6 text-white" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2L13.09 8.26L19 9.27L13.18 14.14L14.18 20.02L12 17.77L9.82 20.02L10.82 14.14L5 9.27L10.91 8.26L12 2Z" />
              </svg>
            </div>
            <p className="text-muted-foreground text-sm">Verificando acesso...</p>
          </div>
        </div>
      );
    }

    // User is authorized admin
    return <Component {...props} />;
  };

  return AdminAuthComponent;
};

export default withAdminAuth;