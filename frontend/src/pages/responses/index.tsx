import { useState, useEffect } from 'react';
import withAuth from '@/components/withAuth';
import api from '@/lib/api';
import { FormResponse } from '@/types';
import Link from 'next/link';

function MyResponsesPage() {
  const [responses, setResponses] = useState<FormResponse[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/forms-management/responses')
      .then(res => setResponses(res.data))
      .catch(err => console.error("Failed to fetch responses", err))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p>Loading your responses...</p>;

  return (
    <div>
      <h1 className="text-3xl font-bold mb-4">My Submitted Forms</h1>
      <div className="space-y-4">
        {responses.length > 0 ? responses.map(res => (
          <Link key={res.id} href={`/responses/${res.id}`} className="block p-4 bg-white rounded shadow hover:shadow-md transition-shadow">
            <div className="flex justify-between">
              <h2 className="font-bold">Response ID: {res.id}</h2>
              <span className="text-sm text-gray-600">{new Date(res.submitted_at).toLocaleString()}</span>
            </div>
            <p className="text-sm capitalize">Status: {res.status}</p>
          </Link>
        )) : (
          <p>You have not submitted any forms yet.</p>
        )}
      </div>
    </div>
  );
}

export default withAuth(MyResponsesPage);