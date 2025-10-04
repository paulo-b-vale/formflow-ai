import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import api from '@/lib/api';
import withAdminAuth from '@/components/withAdminAuth';
import { FormTemplate } from '@/types';
import Link from 'next/link';

function FormPreviewPage() {
  const router = useRouter();
  const { id } = router.query;
  const [template, setTemplate] = useState<FormTemplate | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (id) {
      api.get(`/forms-management/templates/${id}`)
        .then(res => setTemplate(res.data))
        .catch(err => console.error("Failed to fetch template", err))
        .finally(() => setLoading(false));
    }
  }, [id]);

  if (loading) return <p>Loading preview...</p>;
  if (!template) return <p>Form template not found.</p>;

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-3xl font-bold">Preview: {template.title}</h1>
        <Link href={`/admin/forms/${id}/edit`} className="bg-blue-500 text-white py-2 px-4 rounded hover:bg-blue-600">
          Edit Form
        </Link>
      </div>
      <div className="bg-white p-6 rounded-lg shadow-md space-y-6">
        {template.description && <p className="text-gray-600 italic">{template.description}</p>}
        {template.fields.map(field => (
          <div key={field.field_id}>
            <label className="block font-bold mb-1">
              {field.label} {field.required && <span className="text-red-500">*</span>}
            </label>
            {field.description && <p className="text-sm text-gray-500 mb-2">{field.description}</p>}
            {field.field_type === 'select' ? (
              <select className="w-full p-2 border rounded bg-gray-100" disabled>
                <option>-- Select an option --</option>
                {field.options?.map(opt => <option key={opt}>{opt}</option>)}
              </select>
            ) : field.field_type === 'textarea' ? (
               <textarea className="w-full p-2 border rounded bg-gray-100" rows={4} disabled placeholder={field.placeholder || ''}/>
            ) : (
              <input 
                type={field.field_type === 'boolean' ? 'checkbox' : field.field_type} 
                className="w-full p-2 border rounded bg-gray-100" 
                disabled 
                placeholder={field.placeholder || ''}
              />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default withAdminAuth(FormPreviewPage);