import { useState, useEffect } from 'react';
import withAuth from '@/components/withAuth';
import { useRouter } from 'next/router';
import api from '@/lib/api';
import { FormResponse } from '@/types';

function ResponseDetailPage() {
  const router = useRouter();
  const { id } = router.query;
  const [response, setResponse] = useState<FormResponse | null>(null);

  useEffect(() => {
    if (id) {
      api.get(`/forms-management/responses/${id}`)
        .then(res => setResponse(res.data))
        .catch(err => console.error("Failed to fetch response details", err));
    }
  }, [id]);

  if (!response) return <p>Loading response details...</p>;

  return (
    <div className="bg-white p-6 rounded shadow">
      <h1 className="text-2xl font-bold mb-4">Response Details</h1>
      <p><strong>Submitted by:</strong> {response.respondent_name}</p>
      <p><strong>Date:</strong> {new Date(response.submitted_at).toLocaleString()}</p>
      <p><strong>Status:</strong> <span className="capitalize">{response.status}</span></p>
      <hr className="my-4" />
      <h2 className="text-xl font-semibold mb-2">Submitted Answers</h2>
      <div className="space-y-2">
        {Object.entries(response.responses).map(([key, value]) => (
          <div key={key}>
            <p className="font-bold capitalize">{key.replace(/_/g, ' ')}:</p>
            <p className="pl-2">{String(value)}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export default withAuth(ResponseDetailPage);