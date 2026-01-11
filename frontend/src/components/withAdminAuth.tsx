import { useAuth } from '@/hooks/useAuth';
import { useRouter } from 'next/router';
import { useEffect, ComponentType, useState } from 'react';

const withAdminAuth = <P extends object>(Component: ComponentType<P>) => {
  const AdminAuthComponent = (props: P) => {
    const { user, loading } = useAuth();
    const router = useRouter();
    const [isChecking, setIsChecking] = useState(true);

    useEffect(() => {
      // Give auth context time to load from localStorage
      const timer = setTimeout(() => {
        setIsChecking(false);
        if (!loading && (!user || user.role !== 'admin')) {
          router.push('/login');
        }
      }, 200);

      return () => clearTimeout(timer);
    }, [user, loading, router]);

    // Show loading while checking auth or loading user
    if (loading || isChecking) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-background">
          <div className="flex flex-col items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500 via-pink-500 to-orange-400 flex items-center justify-center animate-pulse">
              <svg className="w-6 h-6 text-white" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2L13.09 8.26L19 9.27L13.18 14.14L14.18 20.02L12 17.77L9.82 20.02L10.82 14.14L5 9.27L10.91 8.26L12 2Z" />
              </svg>
            </div>
            <p className="text-muted-foreground text-sm">Verifying access...</p>
          </div>
        </div>
      );
    }

    // After loading, check if user is admin
    if (!user || user.role !== 'admin') {
      return (
        <div className="min-h-screen flex items-center justify-center bg-background">
          <div className="flex flex-col items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-destructive/20 flex items-center justify-center">
              <svg className="w-6 h-6 text-destructive" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <p className="text-muted-foreground text-sm">Admin access required</p>
            <p className="text-xs text-muted-foreground">Redirecting to login...</p>
          </div>
        </div>
      );
    }

    return <Component {...props} />;
  };

  return AdminAuthComponent;
};

export default withAdminAuth;