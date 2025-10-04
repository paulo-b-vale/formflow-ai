import Link from 'next/link';
import { ReactNode } from 'react';
import { useRouter } from 'next/router';

interface AdminLayoutProps {
  children: ReactNode;
}

const navItems = [
  { name: 'Dashboard', href: '/admin' },
  { name: 'Analytics', href: '/admin/analytics' },
  { name: 'Users', href: '/admin/users' },
  { name: 'Contexts', href: '/admin/contexts' },
  { name: 'Forms', href: '/admin/forms' },
  { name: 'Responses', href: '/admin/responses' },
  { name: 'Assignments', href: '/admin/assignments' },
];

export default function AdminLayout({ children }: AdminLayoutProps) {
  const router = useRouter();

  return (
    <div className="flex">
      <aside className="w-64 bg-gray-100 p-4 border-r">
        <h2 className="font-bold text-xl mb-4">Admin Menu</h2>
        <nav>
          <ul>
            {navItems.map((item) => (
              <li key={item.name}>
                <Link
                  href={item.href}
                  className={`block py-2 px-3 rounded ${
                    router.pathname.startsWith(item.href) ? 'bg-blue-500 text-white' : 'hover:bg-gray-200'
                  }`}
                >
                  {item.name}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      </aside>
      <main className="flex-grow p-6">
        {children}
      </main>
    </div>
  );
}