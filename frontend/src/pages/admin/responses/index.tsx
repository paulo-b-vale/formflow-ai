import { useState, useEffect } from 'react';
import Link from 'next/link';
import api from '@/lib/api';
import withAdminAuth from '@/components/withAdminAuth';
import { FormResponse, FormTemplate } from '@/types';
import { useDebounce } from '@/hooks/useDebounce';

function AdminResponsesPage() {
  const [responses, setResponses] = useState<FormResponse[]>([]);
  const [templates, setTemplates] = useState<FormTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  
  const [statusFilter, setStatusFilter] = useState('');
  const [templateFilter, setTemplateFilter] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const debouncedSearchTerm = useDebounce(searchTerm, 500);

  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        const [responsesRes, templatesRes] = await Promise.all([
          api.get('/forms-management/responses'),
          api.get('/forms-management/templates')
        ]);
        setResponses(responsesRes.data);
        setTemplates(templatesRes.data);
      } catch (err) {
        console.error("Failed to fetch initial data", err);
      } finally {
        setLoading(false);
      }
    };
    fetchInitialData();
  }, []);

  useEffect(() => {
    const fetchResponses = async () => {
      setLoading(true);
      try {
        const params = new URLSearchParams();
        if (statusFilter) params.append('status', statusFilter);
        if (templateFilter) params.append('form_template_id', templateFilter);
        if (debouncedSearchTerm) params.append('search_term', debouncedSearchTerm);
        
        const res = await api.get(`/forms-management/responses?${params.toString()}`);
        setResponses(res.data);
      } catch (err) {
        console.error("Failed to fetch responses", err);
      } finally {
        setLoading(false);
      }
    };
    
    fetchResponses();
  }, [statusFilter, templateFilter, debouncedSearchTerm]);

  if (loading && responses.length === 0) return <p>Loading responses...</p>;

  return (
    <div>
      <h1 className="text-3xl font-bold mb-4">Form Responses</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4 bg-gray-50 p-4 rounded-lg">
        <input
          type="text"
          placeholder="Search by name..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="p-2 border rounded"
        />
        <select value={templateFilter} onChange={(e) => setTemplateFilter(e.target.value)} className="p-2 border rounded">
          <option value="">All Forms</option>
          {templates.map(t => <option key={t.id} value={t.id}>{t.title}</option>)}
        </select>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="p-2 border rounded">
          <option value="">All Statuses</option>
          <option value="complete">Complete</option>
          <option value="pending_review">Pending Review</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
        </select>
      </div>

      <div className="bg-white rounded shadow-md overflow-x-auto">
        <table className="min-w-full">
          {/* ... table header ... */}
          <tbody>
            {loading ? (
                <tr><td colSpan={5} className="text-center p-4">Loading...</td></tr>
            ) : responses.length > 0 ? responses.map(res => (
              <tr key={res.id} className="hover:bg-gray-50">
                <td className="py-2 px-4 border-b">{res.respondent_name}</td>
                <td className="py-2 px-4 border-b">
                    <span className={`px-2 py-1 text-xs font-semibold rounded-full capitalize ${
                        res.status === 'approved' ? 'bg-green-200 text-green-800' :
                        res.status === 'rejected' ? 'bg-red-200 text-red-800' :
                        res.status === 'pending_review' ? 'bg-yellow-200 text-yellow-800' :
                        'bg-gray-200 text-gray-800'
                    }`}>
                        {res.status.replace(/_/g, ' ')}
                    </span>
                </td>
                <td className="py-2 px-4 border-b">{new Date(res.submitted_at).toLocaleString()}</td>
                <td className="py-2 px-4 border-b">
                  <Link href={`/admin/responses/${res.id}`} className="text-blue-500 hover:underline">
                    View Details
                  </Link>
                </td>
              </tr>
            )) : (
              <tr><td colSpan={5} className="text-center p-4">No responses found for the selected filters.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default withAdminAuth(AdminResponsesPage);