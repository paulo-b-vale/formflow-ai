import { useState, useEffect, FormEvent } from 'react';
import api from '@/lib/api';
import withAdminAuth from '@/components/withAdminAuth';
import { User } from '@/types';
import { useRouter } from 'next/router';

function NewContextPage() {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [contextType, setContextType] = useState('other');
  const [users, setUsers] = useState<User[]>([]);
  const [assignedUsers, setAssignedUsers] = useState<string[]>([]);
  const router = useRouter();

  useEffect(() => {
    api.get('/users/').then(response => setUsers(response.data));
  }, []);

  const handleUserToggle = (userId: string) => {
    setAssignedUsers(prev =>
      prev.includes(userId) ? prev.filter(id => id !== userId) : [...prev, userId]
    );
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
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
    }
  };

  return (
    <div>
      <h1 className="text-3xl font-bold mb-4">Create New Context</h1>
      <form onSubmit={handleSubmit} className="space-y-6 bg-white p-6 rounded shadow">
        <div>
          <label className="block font-bold mb-1">Title</label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full p-2 border rounded"
            required
          />
        </div>
        <div>
          <label className="block font-bold mb-1">Description</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="w-full p-2 border rounded"
          />
        </div>
        <div>
          <label className="block font-bold mb-1">Context Type</label>
          <select value={contextType} onChange={(e) => setContextType(e.target.value)} className="w-full p-2 border rounded">
            <option value="hospital">Hospital</option>
            <option value="construction">Construction</option>
            <option value="maintenance">Maintenance</option>
            <option value="consulting">Consulting</option>
            <option value="other">Other</option>
          </select>
        </div>
        <div>
          <h3 className="font-bold mb-2">Assign Users</h3>
          <div className="space-y-2 max-h-60 overflow-y-auto border p-2 rounded">
            {users.map(user => (
              <div key={user.id} className="flex items-center">
                <input
                  type="checkbox"
                  id={`user-${user.id}`}
                  checked={assignedUsers.includes(user.id)}
                  onChange={() => handleUserToggle(user.id)}
                  className="mr-2"
                />
                <label htmlFor={`user-${user.id}`}>{user.name} ({user.email})</label>
              </div>
            ))}
          </div>
        </div>
        <button type="submit" className="bg-blue-500 text-white py-2 px-4 rounded hover:bg-blue-600">
          Create Context
        </button>
      </form>
    </div>
  );
}

export default withAdminAuth(NewContextPage);