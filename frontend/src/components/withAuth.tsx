import { useAuth } from '@/hooks/useAuth';
import { useRouter } from 'next/router';
import { useEffect, ComponentType, useState } from 'react';

const withAuth = <P extends object>(Component: ComponentType<P>) => {
  const AuthComponent = (props: P) => {
    const { user } = useAuth();
    const router = useRouter();
    const [isChecking, setIsChecking] = useState(true);

    useEffect(() => {
      // Give a moment for auth to load from localStorage
      const timer = setTimeout(() => {
        setIsChecking(false);
        if (!user) {
          router.push('/login');
        }
      }, 100);

      return () => clearTimeout(timer);
    }, [user, router]);

    // Show loading spinner while checking auth
    if (isChecking) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-background">
          <div className="flex flex-col items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500 via-pink-500 to-orange-400 flex items-center justify-center animate-pulse">
              <svg className="w-6 h-6 text-white" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2L13.09 8.26L19 9.27L13.18 14.14L14.18 20.02L12 17.77L9.82 20.02L10.82 14.14L5 9.27L10.91 8.26L12 2Z" />
              </svg>
            </div>
            <p className="text-muted-foreground text-sm">Loading...</p>
          </div>
        </div>
      );
    }

    if (!user) {
      // Show redirecting message
      return (
        <div className="min-h-screen flex items-center justify-center bg-background">
          <div className="flex flex-col items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500 via-pink-500 to-orange-400 flex items-center justify-center">
              <svg className="w-6 h-6 text-white" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2L13.09 8.26L19 9.27L13.18 14.14L14.18 20.02L12 17.77L9.82 20.02L10.82 14.14L5 9.27L10.91 8.26L12 2Z" />
              </svg>
            </div>
            <p className="text-muted-foreground text-sm">Redirecting to login...</p>
          </div>
        </div>
      );
    }

    return <Component {...props} />;
  };

  return AuthComponent;
};

export default withAuth;