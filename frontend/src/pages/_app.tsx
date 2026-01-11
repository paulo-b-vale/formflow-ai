import '@/styles/globals.css'
import type { AppProps } from 'next/app'
import { AuthProvider } from '@/contexts/AuthContext'
import { ThemeProvider } from '@/contexts/ThemeContext'
import Layout from '@/components/Layout'
import AdminLayout from '@/components/AdminLayout'
import { useRouter } from 'next/router'

// Pages that should NOT have the standard Layout wrapper
const noLayoutPages = ['/', '/login', '/register'];

export default function App({ Component, pageProps }: AppProps) {
  const router = useRouter();
  const isAdminRoute = router.pathname.startsWith('/admin');
  const isNoLayoutPage = noLayoutPages.includes(router.pathname);

  return (
    <ThemeProvider>
      <AuthProvider>
        {isNoLayoutPage ? (
          // Full-page layouts (landing, login, register)
          <Component {...pageProps} />
        ) : isAdminRoute ? (
          // Admin pages with admin layout
          <Layout>
            <AdminLayout>
              <Component {...pageProps} />
            </AdminLayout>
          </Layout>
        ) : (
          // Regular pages with standard layout
          <Layout>
            <Component {...pageProps} />
          </Layout>
        )}
      </AuthProvider>
    </ThemeProvider>
  )
}