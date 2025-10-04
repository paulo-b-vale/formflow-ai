import { useAuth } from '@/hooks/useAuth';
import { useRouter } from 'next/router';
import { useEffect, ComponentType } from 'react';

const withAuth = <P extends object>(Component: ComponentType<P>) => {
  const AuthComponent = (props: P) => {
    const { user } = useAuth();
    const router = useRouter();

    useEffect(() => {
      if (!user) {
        router.push('/login');
      }
    }, [user, router]);

    if (!user) {
      return null; // Or a loading spinner
    }

    return <Component {...props} />;
  };

  return AuthComponent;
};

export default withAuth;