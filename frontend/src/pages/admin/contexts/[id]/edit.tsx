// frontend/src/pages/admin/contexts/[id]/edit.tsx
import { useState, useEffect, FormEvent } from 'react';
import { useRouter } from 'next/router';
import api from '@/lib/api';
import withAdminAuth from '@/components/withAdminAuth';
import { User, WorkContext } from '@/types';

function EditContextPage() {
  const router = useRouter();
  const { id } = router.query;

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [contextType, setContextType] = useState('other');
  const [isActive, setIsActive] = useState(true);
  const [users, setUsers] = useState<User[]>([]);
  const [assignedUsers, setAssignedUsers] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;

    const fetchData = async () => {
      try {
        const [contextRes, usersRes] = await Promise.all([
          api.get(`/forms-management/contexts/${id}`),
          api.get('/users/'),
        ]);
        
        const context: WorkContext = contextRes.data;
        setTitle(context.title);
        setDescription(context.description);
        setContextType(context.context_type);
        setAssignedUsers(context.assigned_users);
        // setIsActive(context.is_active);
        setUsers(usersRes.data);

      } catch (error) {
        console.error('Failed to fetch data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [id]);

  const handleUserToggle = (userId: string) => {
    setAssignedUsers(prev =>
      prev.includes(userId) ? prev.filter(id => id !== userId) : [...prev, userId]
    );
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await api.put(`/forms-management/contexts/${id}`, {
        title,
        description,
        context_type: contextType,
        assigned_users: assignedUsers,
        is_active: isActive,
      });
      router.push('/admin/contexts');
    } catch (error) {
      console.error('Failed to update context:', error);
      alert('Failed to update context.');
    }
  };
  
    const handleDelete = async () => {
    if (window.confirm('Are you sure you want to deactivate this context?')) {
      try {
        await api.delete(`/forms-management/contexts/${id}`);
        router.push('/admin/contexts');
      } catch (error) {
        console.error('Failed to delete context:', error);
        alert('Failed to delete context.');
      }
    }
  };

  if (loading) return <p>Loading context...</p>;

  return (
    <div>
      <h1 className="text-3xl font-bold mb-4">Edit Context</h1>
      <form onSubmit={handleSubmit} className="space-y-6 bg-white p-6 rounded shadow">
        {/* Form fields are identical to the 'new' page, but pre-filled */}
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
        <div className="flex justify-between items-center">
            <button type="submit" className="bg-blue-500 text-white py-2 px-4 rounded hover:bg-blue-600">
              Save Changes
            </button>
            <button type="button" onClick={handleDelete} className="bg-red-500 text-white py-2 px-4 rounded hover:bg-red-600">
              Deactivate Context
            </button>
        </div>
      </form>
    </div>
  );
}

export default withAdminAuth(EditContextPage);