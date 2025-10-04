import { createContext, useState, useEffect, ReactNode } from 'react';
import { useRouter } from 'next/router';
import api from '@/lib/api';
import { User } from '@/types'; // Import the User type

// Update AuthContextType to use the imported User type
interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (identifier: string, password: string) => Promise<void>;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider = ({ children }: AuthProviderProps) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true); // Add loading state
  const router = useRouter();

  useEffect(() => {
    const checkUser = async () => {
      const token = localStorage.getItem('token');
      if (token) {
        try {
          const response = await api.get('/users/me');
          setUser(response.data);
        } catch (error) {
          console.error("Session expired or invalid", error);
          // Clear invalid token
          localStorage.removeItem('token');
        }
      }
      setLoading(false);
    };
    checkUser();
  }, []);

  const login = async (identifier: string, password: string) => {
    try {
      // Check if identifier looks like a phone number (contains digits and starts with +)
      const isPhoneLogin = identifier.startsWith('+') || /^\d+$/.test(identifier.replace(/[^\d]/g, ''));
      
      let response;
      if (isPhoneLogin) {
        // Phone login
        response = await api.post('/auth/phone-login', {
          phone_number: identifier,
          password
        });
      } else {
        // Email login - use existing flow
        const formData = new URLSearchParams();
        formData.append('username', identifier);
        formData.append('password', password);
        
        response = await api.post('/auth/login', formData, {
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        });
      }

      const { access_token } = response.data.tokens;
      const userData = response.data.user;

      localStorage.setItem('token', access_token);
      setUser(userData);
      
      // Redirect based on role
      if (userData.role === 'admin') {
        router.push('/admin');
      } else {
        router.push('/dashboard');
      }
    } catch (error) {
      console.error('Login failed:', error);
      alert('Login failed. Please check your credentials.');
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    setUser(null);
    router.push('/login');
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};