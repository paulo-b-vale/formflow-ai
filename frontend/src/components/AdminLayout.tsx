import Link from 'next/link';
import { ReactNode } from 'react';
import { useRouter } from 'next/router';
import { LayoutDashboard, Users, FolderKanban, FileText, BarChart3, Settings, ClipboardList } from 'lucide-react';

interface AdminLayoutProps {
  children: ReactNode;
}

const navItems = [
  { name: 'Dashboard', href: '/admin', icon: LayoutDashboard },
  { name: 'Analytics', href: '/admin/analytics', icon: BarChart3 },
  { name: 'Users', href: '/admin/users', icon: Users },
  { name: 'Contexts', href: '/admin/contexts', icon: FolderKanban },
  { name: 'Forms', href: '/admin/forms', icon: FileText },
  { name: 'Responses', href: '/admin/responses', icon: ClipboardList },
  { name: 'Assignments', href: '/admin/assignments', icon: Settings },
];

export default function AdminLayout({ children }: AdminLayoutProps) {
  const router = useRouter();

  return (
    <div className="flex min-h-screen bg-background text-foreground">
      {/* Sidebar */}
      <aside className="w-64 bg-card border-r border-border flex flex-col sticky top-0 h-screen overflow-y-auto">
        <div className="p-6 border-b border-border/50">
          <h2 className="font-bold text-xl tracking-tight text-primary">
            FlowForm Admin
          </h2>
        </div>

        <nav className="flex-1 p-4">
          <ul className="space-y-1.5">
            {navItems.map((item) => {
              const isActive = router.pathname === item.href || (item.href !== '/admin' && router.pathname.startsWith(item.href));
              return (
                <li key={item.name}>
                  <Link
                    href={item.href}
                    className={`flex items-center gap-3 py-2.5 px-3 rounded-xl transition-all duration-200 group ${isActive
                        ? 'bg-primary/10 text-primary font-semibold shadow-sm ring-1 ring-primary/20'
                        : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                      }`}
                  >
                    <item.icon className={`w-4.5 h-4.5 transition-colors ${isActive ? 'text-primary' : 'group-hover:text-primary'}`} />
                    <span className="text-sm">{item.name}</span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        <div className="p-6 border-t border-border/50">
          <div className="bg-muted/50 rounded-2xl p-4 text-[10px] text-muted-foreground">
            <p className="font-semibold text-foreground/70 mb-1 uppercase tracking-wider">System Status</p>
            <div className="flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
              System Operational
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-grow overflow-x-hidden">
        <div className="container py-0 h-full">
          {children}
        </div>
      </main>
    </div>
  );
}