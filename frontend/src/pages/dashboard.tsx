import withAuth from '@/components/withAuth';
import { useAuth } from '@/hooks/useAuth';
import Link from 'next/link';
import { useEffect, useState } from 'react';

function Dashboard() {
  const { user } = useAuth();
  const [mounted, setMounted] = useState(false);
  const [greeting, setGreeting] = useState('');

  useEffect(() => {
    setMounted(true);
    const hour = new Date().getHours();
    if (hour < 12) setGreeting('Good morning');
    else if (hour < 18) setGreeting('Good afternoon');
    else setGreeting('Good evening');
  }, []);

  const stats = [
    { label: 'Forms Completed', value: '12', icon: '📋', color: 'from-blue-500 to-blue-600' },
    { label: 'Active Contexts', value: '3', icon: '🎯', color: 'from-teal-500 to-teal-600' },
    { label: 'Responses', value: '48', icon: '✅', color: 'from-slate-500 to-slate-600' },
  ];

  const quickActions = [
    {
      title: 'Start Chat',
      description: 'Begin a new conversation with the AI assistant',
      href: '/chat',
      icon: (
        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
        </svg>
      ),
      gradient: 'from-blue-500 to-teal-500'
    },
    {
      title: 'My Responses',
      description: 'View your submitted form responses',
      href: '/responses',
      icon: (
        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      ),
      gradient: 'from-slate-500 to-blue-500'
    },
  ];

  return (
    <div className="min-h-screen bg-background relative">
      {/* Background orbs */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="gradient-orb w-96 h-96 -top-48 -right-48 opacity-30" />
        <div className="gradient-orb w-80 h-80 bottom-0 -left-40 bg-teal-500/20 opacity-30" />
      </div>

      <div className="relative z-10 max-w-6xl mx-auto px-6 py-12">
        {/* Welcome Section */}
        <div className={`mb-12 ${mounted ? 'animate-fade-in' : 'opacity-0'}`}>
          <h1 className="text-4xl font-bold mb-2">
            {greeting}, <span className="gradient-text dark:gradient-text-dark">{user?.name}</span>!
          </h1>
          <p className="text-muted-foreground text-lg">
            Here's an overview of your FlowForm activity.
          </p>
        </div>

        {/* Stats Grid */}
        <div className={`grid grid-cols-1 md:grid-cols-3 gap-6 mb-12 ${mounted ? 'animate-slide-up' : 'opacity-0'}`} style={{ animationDelay: '0.1s' }}>
          {stats.map((stat, index) => (
            <div
              key={stat.label}
              className="card-glass p-6 hover-lift"
              style={{ animationDelay: `${0.1 + index * 0.1}s` }}
            >
              <div className="flex items-center justify-between mb-4">
                <span className="text-3xl">{stat.icon}</span>
                <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${stat.color} opacity-20`} />
              </div>
              <p className="text-3xl font-bold mb-1">{stat.value}</p>
              <p className="text-muted-foreground text-sm">{stat.label}</p>
            </div>
          ))}
        </div>

        {/* Quick Actions */}
        <div className={`${mounted ? 'animate-slide-up' : 'opacity-0'}`} style={{ animationDelay: '0.3s' }}>
          <h2 className="text-2xl font-bold mb-6">Quick Actions</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {quickActions.map((action) => (
              <Link
                key={action.title}
                href={action.href}
                className="group card-glass p-6 hover-lift flex items-start gap-4"
              >
                <div className={`w-14 h-14 rounded-xl bg-gradient-to-br ${action.gradient} flex items-center justify-center text-white flex-shrink-0 group-hover:scale-110 transition-transform`}>
                  {action.icon}
                </div>
                <div>
                  <h3 className="text-xl font-semibold mb-1 group-hover:text-blue-500 transition-colors">
                    {action.title}
                  </h3>
                  <p className="text-muted-foreground">{action.description}</p>
                </div>
              </Link>
            ))}
          </div>
        </div>

        {/* Tips Section */}
        <div className={`mt-12 ${mounted ? 'animate-fade-in' : 'opacity-0'}`} style={{ animationDelay: '0.5s' }}>
          <div className="card-gradient p-6">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 rounded-xl bg-white/20 flex items-center justify-center flex-shrink-0">
                <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div>
                <h3 className="text-xl font-semibold text-white mb-2">Pro Tip</h3>
                <p className="text-white/80">
                  Start a chat and describe what you want to do in natural language.
                  Our AI will automatically identify the right form and guide you through the process.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default withAuth(Dashboard);