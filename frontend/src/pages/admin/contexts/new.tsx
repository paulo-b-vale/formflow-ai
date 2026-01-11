import { useState, useEffect, FormEvent } from 'react';
import api from '@/lib/api';
import withAdminAuth from '@/components/withAdminAuth';
import { User } from '@/types';
import { useRouter } from 'next/router';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { ArrowLeft, Users, FolderPlus, Info } from 'lucide-react';
import Link from 'next/link';
import { motion } from 'framer-motion';

function NewContextPage() {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [contextType, setContextType] = useState('other');
  const [users, setUsers] = useState<User[]>([]);
  const [assignedUsers, setAssignedUsers] = useState<string[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const router = useRouter();

  useEffect(() => {
    const fetchUsers = async () => {
      try {
        const response = await api.get('/users/');
        setUsers(response.data);
      } catch (error) {
        console.error('Failed to fetch users:', error);
      }
    };
    fetchUsers();
  }, []);

  const handleUserToggle = (userId: string) => {
    setAssignedUsers(prev =>
      prev.includes(userId) ? prev.filter(id => id !== userId) : [...prev, userId]
    );
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await api.post('/forms-management/contexts', {
        title,
        description,
        context_type: contextType,
        assigned_users: assignedUsers,
      });
      router.push('/admin/contexts');
    } catch (error) {
      console.error('Failed to create context:', error);
      alert('Failed to create context.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      <motion.div
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        className="mb-6"
      >
        <Link href="/admin/contexts" className="text-sm text-muted-foreground hover:text-primary transition-colors flex items-center gap-1">
          <ArrowLeft className="w-4 h-4" />
          Back to Contexts
        </Link>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
      >
        <Card className="border-0 shadow-xl overflow-hidden">
          <div className="h-2 bg-gradient-to-r from-purple-500 via-pink-500 to-orange-400" />
          <CardHeader className="pt-8 px-8">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                <FolderPlus className="w-6 h-6 text-primary" />
              </div>
              <div>
                <CardTitle className="text-2xl font-bold tracking-tight">Create New Context</CardTitle>
                <CardDescription>Define a new work environment and assign users</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-8">
            <form onSubmit={handleSubmit} className="space-y-8">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                {/* Basic Info */}
                <div className="space-y-6">
                  <div className="space-y-2">
                    <Label htmlFor="title" className="text-sm font-semibold">Context Title</Label>
                    <Input
                      id="title"
                      placeholder="e.g., Emergency Department"
                      value={title}
                      onChange={(e) => setTitle(e.target.value)}
                      className="h-11 border-muted-foreground/20 focus-visible:ring-primary"
                      required
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="type" className="text-sm font-semibold">Context Type</Label>
                    <Select value={contextType} onValueChange={setContextType}>
                      <SelectTrigger className="h-11 border-muted-foreground/20">
                        <SelectValue placeholder="Select type" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="hospital">Hospital</SelectItem>
                        <SelectItem value="construction">Construction</SelectItem>
                        <SelectItem value="maintenance">Maintenance</SelectItem>
                        <SelectItem value="consulting">Consulting</SelectItem>
                        <SelectItem value="other">Other</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="description" className="text-sm font-semibold text-foreground/80">Description</Label>
                    <Textarea
                      id="description"
                      placeholder="What is this context used for?"
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      className="min-h-[120px] border-muted-foreground/20 focus-visible:ring-primary resize-none"
                    />
                  </div>
                </div>

                {/* User Assignment */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <Label className="text-sm font-semibold flex items-center gap-2">
                      <Users className="w-4 h-4 text-primary" />
                      Assign Users
                    </Label>
                    <Badge variant="secondary" className="rounded-full">
                      {assignedUsers.length} Selected
                    </Badge>
                  </div>

                  <div className="border border-muted-foreground/10 rounded-xl p-1 bg-muted/30">
                    <div className="max-h-[300px] overflow-y-auto space-y-1 p-2 custom-scrollbar">
                      {users.length > 0 ? (
                        users.map(user => (
                          <div
                            key={user.id}
                            className={`flex items-center gap-3 p-3 rounded-lg transition-all cursor-pointer hover:bg-background ${assignedUsers.includes(user.id) ? 'bg-background shadow-sm ring-1 ring-primary/20' : ''
                              }`}
                            onClick={() => handleUserToggle(user.id)}
                          >
                            <Checkbox
                              checked={assignedUsers.includes(user.id)}
                              onCheckedChange={() => handleUserToggle(user.id)}
                              className="rounded-sm"
                            />
                            <div className="flex flex-col">
                              <span className="text-sm font-medium leading-none">{user.name}</span>
                              <span className="text-xs text-muted-foreground mt-1">{user.email}</span>
                            </div>
                          </div>
                        ))
                      ) : (
                        <div className="py-8 text-center text-muted-foreground text-sm flex flex-col items-center gap-2">
                          <Info className="w-5 h-5 opacity-40" />
                          No users available to assign
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              <div className="pt-4 flex justify-end gap-3 border-t border-border/50">
                <Link href="/admin/contexts">
                  <Button variant="ghost" type="button" className="h-11 px-8 rounded-full">
                    Cancel
                  </Button>
                </Link>
                <Button
                  type="submit"
                  disabled={isSubmitting}
                  className="h-11 px-10 rounded-full shadow-lg hover:shadow-xl transition-all"
                >
                  {isSubmitting ? 'Creating...' : 'Create Context'}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}

export default withAdminAuth(NewContextPage);