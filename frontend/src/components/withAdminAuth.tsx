import { useAuth } from '@/hooks/useAuth';
import { useRouter } from 'next/router';
import { useEffect, ComponentType } from 'react';

const withAdminAuth = <P extends object>(Component: ComponentType<P>) => {
  const AdminAuthComponent = (props: P) => {
    const { user, loading } = useAuth();
    const router = useRouter();

    useEffect(() => {
      if (!loading && (!user || user.role !== 'admin')) {
        router.push('/login');
      }
    }, [user, loading, router]);

    if (loading || !user || user.role !== 'admin') {
      return <div>Loading...</div>; // Or a loading spinner
    }

    return <Component {...props} />;
  };

  return AdminAuthComponent;
};

export default withAdminAuth;