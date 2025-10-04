import { useState, useEffect } from 'react';
import api from '@/lib/api';
import withAdminAuth from '@/components/withAdminAuth';
import { WorkContext } from '@/types';
import Link from 'next/link';

function ContextsPage() {
  const [contexts, setContexts] = useState<WorkContext[]>([]);

  useEffect(() => {
    const fetchContexts = async () => {
      try {
        const response = await api.get('/forms-management/contexts');
        setContexts(response.data);
      } catch (error) {
        console.error('Failed to fetch contexts:', error);
      }
    };
    fetchContexts();
  }, []);

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-3xl font-bold">Context Management</h1>
        <Link href="/admin/contexts/new" className="bg-blue-500 text-white py-2 px-4 rounded hover:bg-blue-600">
          Create New Context
        </Link>
      </div>
      <div className="bg-white p-4 rounded shadow">
        {contexts.length > 0 ? (
          <ul>
            {contexts.map((context) => (
              <li key={context.id} className="border-b last:border-b-0 py-2">
                <h3 className="font-bold">{context.title}</h3>
                <p className="text-sm text-gray-600">{context.description}</p>
                <span className="text-xs bg-gray-200 px-2 py-1 rounded-full">{context.context_type}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p>No contexts found.</p>
        )}
      </div>
    </div>
  );
}

export default withAdminAuth(ContextsPage);