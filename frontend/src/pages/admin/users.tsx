import { useState, useEffect } from 'react';
import api from '@/lib/api';
import withAdminAuth from '@/components/withAdminAuth';
import { User } from '@/types';
import Link from 'next/link';
import { Card, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/badge';
import { motion } from 'framer-motion';

function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchUsers = async () => {
      try {
        const response = await api.get('/users/');
        setUsers(response.data);
      } catch (error) {
        console.error('Failed to fetch users:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchUsers();
  }, []);

  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map((n) => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  const getAvatarColor = (name: string) => {
    const colors = [
      'bg-purple-500',
      'bg-blue-500',
      'bg-green-500',
      'bg-orange-500',
      'bg-pink-500',
      'bg-teal-500',
    ];
    const index = name.charCodeAt(0) % colors.length;
    return colors[index];
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-pulse text-muted-foreground">Loading users...</div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto py-8 px-4">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight">User Management</h1>
        <p className="text-muted-foreground mt-1">Manage your team members and their roles</p>
      </div>

      {/* Users Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {users.map((user, index) => (
          <motion.div
            key={user.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.05 }}
          >
            <Card className="group hover:shadow-lg transition-all duration-300 hover:-translate-y-1 border-0 shadow-sm">
              <CardContent className="p-5">
                <div className="flex items-center gap-4">
                  {/* Avatar */}
                  <div
                    className={`w-12 h-12 rounded-full flex items-center justify-center text-white font-semibold ${getAvatarColor(
                      user.name
                    )}`}
                  >
                    {getInitials(user.name)}
                  </div>

                  {/* User Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold text-foreground truncate">{user.name}</h3>
                      <Badge
                        variant={user.is_active ? 'default' : 'secondary'}
                        className="rounded-full text-xs"
                      >
                        {user.is_active ? 'Active' : 'Inactive'}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground truncate">{user.email}</p>
                    <p className="text-xs text-muted-foreground capitalize mt-1">
                      {user.role}
                    </p>
                  </div>
                </div>

                {/* Actions */}
                <div className="mt-4 pt-4 border-t border-border">
                  <Link
                    href={`/admin/users/${user.id}/edit`}
                    className="text-sm text-primary hover:underline font-medium"
                  >
                    Edit user →
                  </Link>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>

      {users.length === 0 && (
        <Card className="border-dashed border-2 bg-muted/30">
          <CardContent className="flex flex-col items-center justify-center py-16">
            <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mb-4">
              <svg className="w-8 h-8 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold mb-2">No users found</h3>
            <p className="text-muted-foreground text-center">
              Users will appear here once they register
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export default withAdminAuth(UsersPage);