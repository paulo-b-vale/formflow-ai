import { useState, useEffect } from 'react';
import api from '@/lib/api';
import withAdminAuth from '@/components/withAdminAuth';
import { FormTemplate } from '@/types';
import Link from 'next/link';

function FormsPage() {
  const [templates, setTemplates] = useState<FormTemplate[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchTemplates = async () => {
      try {
        const response = await api.get('/forms-management/templates');
        setTemplates(response.data);
      } catch (error) {
        console.error('Failed to fetch form templates:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchTemplates();
  }, []);

  if (loading) return <div>Loading...</div>;

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-3xl font-bold">Form Templates</h1>
        <Link href="/admin/forms/new" className="bg-blue-500 text-white py-2 px-4 rounded hover:bg-blue-600">
          Create New Template
        </Link>
      </div>
      <div className="bg-white p-4 rounded shadow">
        {templates.length > 0 ? (
          <table className="min-w-full">
            <thead className="bg-gray-200">
              <tr>
                <th className="py-2 px-4 border-b text-left">Title</th>
                <th className="py-2 px-4 border-b text-left">Status</th>
                <th className="py-2 px-4 border-b text-left">Fields</th>
              </tr>
            </thead>
            <tbody>
              {templates.map((template) => (
                <tr key={template.id} className="hover:bg-gray-50">
                  <td className="py-2 px-4 border-b font-medium">{template.title}</td>
                  <td className="py-2 px-4 border-b capitalize">{template.status}</td>
                  <td className="py-2 px-4 border-b">{template.fields.length}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p>No form templates found. Create one to get started!</p>
        )}
      </div>
    </div>
  );
}

export default withAdminAuth(FormsPage);