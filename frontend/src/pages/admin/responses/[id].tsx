import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import api from '@/lib/api';
import withAdminAuth from '@/components/withAdminAuth';
import { FormResponse, FormTemplate } from '@/types';
import ReviewPanel from '@/components/responses/ReviewPanel';

function ResponseDetailPage() {
  const router = useRouter();
  const { id } = router.query;
  const [response, setResponse] = useState<FormResponse | null>(null);
  const [template, setTemplate] = useState<FormTemplate | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    if (!id) return;
    try {
      setLoading(true);
      const res = await api.get(`/forms-management/responses/${id}`);
      setResponse(res.data);
      const templateRes = await api.get(`/forms-management/templates/${res.data.form_template_id}`);
      setTemplate(templateRes.data);
    } catch (err) {
      console.error("Failed to fetch response details", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [id]);

  if (loading) return <p>Loading response details...</p>;
  if (!response || !template) return <p>Could not load response data.</p>;
  
  const getFieldLabel = (fieldId: string) => {
      return template.fields.find(f => f.field_id === fieldId)?.label || fieldId;
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="lg:col-span-2 bg-white p-6 rounded shadow-md">
        <h1 className="text-2xl font-bold mb-4 border-b pb-2">{template.title}</h1>
        <div className="space-y-4">
          <div><strong>Submitted by:</strong> {response.respondent_name}</div>
          <div><strong>Date:</strong> {new Date(response.submitted_at).toLocaleString()}</div>
          <hr />
          <h2 className="text-xl font-semibold mt-4">Submitted Answers</h2>
          <div className="space-y-3 mt-2">
            {Object.entries(response.responses).map(([key, value]) => (
              <div key={key}>
                <p className="font-bold">{getFieldLabel(key)}:</p>
                <p className="pl-2 text-gray-700">{String(value)}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
      <div className="lg:col-span-1">
          <ReviewPanel response={response} onReviewSuccess={fetchData} />
      </div>
    </div>
  );
}

export default withAdminAuth(ResponseDetailPage);