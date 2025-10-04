import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import api from '@/lib/api';
import withAdminAuth from '@/components/withAdminAuth';
import { User, WorkContext } from '@/types';

interface AssignedUser {
  id: string;
  name: string;
  email: string;
  assignment_type: string[];
}

function UserAssignmentsPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [contexts, setContexts] = useState<WorkContext[]>([]);
  const [selectedContext, setSelectedContext] = useState<string>('');
  const [assignedUsers, setAssignedUsers] = useState<AssignedUser[]>([]);
  const [selectedUsers, setSelectedUsers] = useState<string[]>([]);
  const [assignmentType, setAssignmentType] = useState<'users' | 'professionals'>('users');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

  // Fetch users and contexts on component mount
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [usersResponse, contextsResponse] = await Promise.all([
          api.get('/users/'),
          api.get('/forms-management/contexts')
        ]);
        setUsers(usersResponse.data);
        setContexts(contextsResponse.data);
      } catch (error) {
        console.error('Failed to fetch data:', error);
        setMessage({ type: 'error', text: 'Failed to load data' });
      }
    };
    fetchData();
  }, []);

  // Fetch assigned users when context is selected
  useEffect(() => {
    if (selectedContext) {
      fetchAssignedUsers();
    }
  }, [selectedContext]);

  const fetchAssignedUsers = async () => {
    if (!selectedContext) return;

    try {
      setLoading(true);
      const response = await api.get(`/forms-management/contexts/${selectedContext}/users`);
      setAssignedUsers(response.data.users || []);
    } catch (error) {
      console.error('Failed to fetch assigned users:', error);
      setMessage({ type: 'error', text: 'Failed to load assigned users' });
    } finally {
      setLoading(false);
    }
  };

  const handleAssignUsers = async () => {
    if (!selectedContext || selectedUsers.length === 0) {
      setMessage({ type: 'error', text: 'Please select a context and at least one user' });
      return;
    }

    try {
      setLoading(true);
      await api.post(`/forms-management/contexts/${selectedContext}/assign-users`, {
        user_ids: selectedUsers,
        assign_type: assignmentType
      });

      setMessage({ type: 'success', text: `Successfully assigned ${selectedUsers.length} user(s) as ${assignmentType}` });
      setSelectedUsers([]);
      await fetchAssignedUsers(); // Refresh the assigned users list
    } catch (error: any) {
      console.error('Failed to assign users:', error);
      setMessage({ type: 'error', text: error.response?.data?.detail || 'Failed to assign users' });
    } finally {
      setLoading(false);
    }
  };

  const handleRemoveUser = async (userId: string) => {
    if (!selectedContext) return;

    try {
      setLoading(true);
      await api.delete(`/forms-management/contexts/${selectedContext}/users/${userId}`);
      setMessage({ type: 'success', text: 'User removed successfully' });
      await fetchAssignedUsers(); // Refresh the assigned users list
    } catch (error: any) {
      console.error('Failed to remove user:', error);
      setMessage({ type: 'error', text: error.response?.data?.detail || 'Failed to remove user' });
    } finally {
      setLoading(false);
    }
  };

  const toggleUserSelection = (userId: string) => {
    setSelectedUsers(prev =>
      prev.includes(userId)
        ? prev.filter(id => id !== userId)
        : [...prev, userId]
    );
  };

  // Get unassigned users for the selected context
  const unassignedUsers = users.filter(user =>
    !assignedUsers.some(assignedUser => assignedUser.id === user.id)
  );

  return (
    <div className="max-w-6xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">User & Context Assignments</h1>

      {message && (
        <div className={`mb-4 p-4 rounded-md ${
          message.type === 'success' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
        }`}>
          {message.text}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Panel - Context Selection & User Assignment */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-semibold mb-4">Assign Users to Context</h2>

          {/* Context Selection */}
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">Select Context</label>
            <select
              value={selectedContext}
              onChange={(e) => setSelectedContext(e.target.value)}
              className="w-full p-2 border rounded-md"
            >
              <option value="">Choose a context...</option>
              {contexts.map(context => (
                <option key={context.id} value={context.id}>
                  {context.title}
                </option>
              ))}
            </select>
          </div>

          {selectedContext && (
            <>
              {/* Assignment Type Selection */}
              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">Assignment Type</label>
                <div className="flex gap-4">
                  <label className="flex items-center">
                    <input
                      type="radio"
                      value="users"
                      checked={assignmentType === 'users'}
                      onChange={(e) => setAssignmentType(e.target.value as 'users')}
                      className="mr-2"
                    />
                    Users
                  </label>
                  <label className="flex items-center">
                    <input
                      type="radio"
                      value="professionals"
                      checked={assignmentType === 'professionals'}
                      onChange={(e) => setAssignmentType(e.target.value as 'professionals')}
                      className="mr-2"
                    />
                    Professionals
                  </label>
                </div>
              </div>

              {/* User Selection */}
              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">
                  Select Users ({selectedUsers.length} selected)
                </label>
                <div className="max-h-60 overflow-y-auto border rounded-md p-2">
                  {unassignedUsers.length === 0 ? (
                    <p className="text-gray-500 text-center py-4">All users are already assigned to this context</p>
                  ) : (
                    unassignedUsers.map(user => (
                      <label key={user.id} className="flex items-center p-2 hover:bg-gray-50 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={selectedUsers.includes(user.id)}
                          onChange={() => toggleUserSelection(user.id)}
                          className="mr-3"
                        />
                        <div>
                          <div className="font-medium">{user.name}</div>
                          <div className="text-sm text-gray-500">{user.email}</div>
                        </div>
                      </label>
                    ))
                  )}
                </div>
              </div>

              {/* Assign Button */}
              <button
                onClick={handleAssignUsers}
                disabled={loading || selectedUsers.length === 0}
                className="w-full bg-blue-500 text-white py-2 px-4 rounded-md hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Assigning...' : `Assign ${selectedUsers.length} User(s) as ${assignmentType}`}
              </button>
            </>
          )}
        </div>

        {/* Right Panel - Currently Assigned Users */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-semibold mb-4">Currently Assigned Users</h2>

          {!selectedContext ? (
            <p className="text-gray-500 text-center py-8">Select a context to view assigned users</p>
          ) : loading ? (
            <p className="text-center py-8">Loading assigned users...</p>
          ) : assignedUsers.length === 0 ? (
            <p className="text-gray-500 text-center py-8">No users assigned to this context</p>
          ) : (
            <div className="space-y-3">
              {assignedUsers.map(user => (
                <div key={user.id} className="flex items-center justify-between p-3 border rounded-md">
                  <div>
                    <div className="font-medium">{user.name}</div>
                    <div className="text-sm text-gray-500">{user.email}</div>
                    <div className="text-xs text-blue-600">
                      {user.assignment_type.join(', ')}
                    </div>
                  </div>
                  <button
                    onClick={() => handleRemoveUser(user.id)}
                    disabled={loading}
                    className="text-red-500 hover:text-red-700 disabled:opacity-50"
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default withAdminAuth(UserAssignmentsPage);