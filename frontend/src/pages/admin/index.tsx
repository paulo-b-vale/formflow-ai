import withAdminAuth from '@/components/withAdminAuth';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import Link from 'next/link';
import { Users, FileText, Settings, AreaChart, LayoutGrid } from 'lucide-react';
import { motion } from 'framer-motion';

const stats = [
  { name: 'Total Users', value: '12', icon: Users, color: 'text-blue-500', bg: 'bg-blue-500/10' },
  { name: 'Active Forms', value: '8', icon: FileText, color: 'text-purple-500', bg: 'bg-purple-500/10' },
  { name: 'Work Contexts', value: '5', icon: LayoutGrid, color: 'text-pink-500', bg: 'bg-pink-500/10' },
  { name: 'Total Responses', value: '154', icon: AreaChart, color: 'text-orange-500', bg: 'bg-orange-500/10' },
];

const quickActions = [
  { name: 'Manage Users', href: '/admin/users', icon: Users, description: 'View and edit registered users' },
  { name: 'Work Contexts', href: '/admin/contexts', icon: LayoutGrid, description: 'Manage departments and teams' },
  { name: 'Form Templates', href: '/admin/forms', icon: FileText, description: 'Create and edit AI forms' },
  { name: 'Settings', href: '/admin/settings', icon: Settings, description: 'Global application configuration' },
];

function AdminDashboard() {
  return (
    <div className="max-w-6xl mx-auto py-8 px-4">
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight">Admin Dashboard</h1>
        <p className="text-muted-foreground mt-1">System overview and management console</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
        {stats.map((stat, index) => (
          <motion.div
            key={stat.name}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
          >
            <Card className="border-0 shadow-sm bg-card hover:shadow-md transition-shadow">
              <CardContent className="p-6">
                <div className="flex items-center gap-4">
                  <div className={`p-3 rounded-xl ${stat.bg}`}>
                    <stat.icon className={`w-6 h-6 ${stat.color}`} />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">{stat.name}</p>
                    <h3 className="text-2xl font-bold">{stat.value}</h3>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Quick Actions */}
        <section>
          <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
            <Settings className="w-5 h-5 text-primary" />
            Quick Actions
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {quickActions.map((action) => (
              <Link key={action.name} href={action.href}>
                <Card className="h-full hover:bg-muted/30 transition-colors cursor-pointer border-border/50 shadow-sm">
                  <CardContent className="p-4 flex items-start gap-4">
                    <div className="mt-1 p-2 rounded-lg bg-background shadow-inner">
                      <action.icon className="w-5 h-5 text-primary" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-sm">{action.name}</h3>
                      <p className="text-xs text-muted-foreground mt-0.5">{action.description}</p>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        </section>

        {/* System Health / Placeholder */}
        <section>
          <h2 className="text-xl font-bold mb-4">System Status</h2>
          <Card className="bg-gradient-to-br from-primary/5 to-purple-500/5 border-primary/10">
            <CardContent className="p-8 flex flex-col items-center justify-center text-center">
              <div className="w-16 h-16 rounded-full bg-green-500/10 flex items-center justify-center mb-4">
                <div className="w-3 h-3 rounded-full bg-green-500 animate-pulse" />
              </div>
              <h3 className="font-bold text-lg">All Systems Operational</h3>
              <p className="text-sm text-muted-foreground mt-2 max-w-sm">
                Backend API, Database, and AI services are running smoothly.
              </p>
              <Button variant="outline" className="mt-6 rounded-full" size="sm">
                View Detailed Logs
              </Button>
            </CardContent>
          </Card>
        </section>
      </div>
    </div>
  );
}

export default withAdminAuth(AdminDashboard);