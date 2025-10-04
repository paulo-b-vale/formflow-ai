import { useState, useEffect, FormEvent } from 'react';
import { useRouter } from 'next/router';
import api from '@/lib/api';
import withAdminAuth from '@/components/withAdminAuth';
import { WorkContext, FormField, FormTemplate } from '@/types';
import FieldEditor from '@/components/forms/FieldEditor';
import { v4 as uuidv4 } from 'uuid';

function EditFormPage() {
  const router = useRouter();
  const { id } = router.query;
  
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [contextId, setContextId] = useState('');
  const [status, setStatus] = useState<'draft' | 'active' | 'archived'>('draft');
  const [fields, setFields] = useState<FormField[]>([]);
  const [contexts, setContexts] = useState<WorkContext[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    const fetchData = async () => {
      try {
        const [templateRes, contextsRes] = await Promise.all([
          api.get(`/forms-management/templates/${id}`),
          api.get('/forms-management/contexts'),
        ]);
        
        const template: FormTemplate = templateRes.data;
        setTitle(template.title);
        setDescription(template.description);
        setContextId(template.context_id);
        setStatus(template.status);
        setFields(template.fields);
        setContexts(contextsRes.data.filter((c: WorkContext) => c.is_active));
        
      } catch (error) {
        console.error('Failed to fetch form template data:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [id]);

  const addField = () => {
    setFields([...fields, {
      field_id: uuidv4(),
      label: '',
      field_type: 'text',
      required: false,
      description: '',
      options: [],
    }]);
  };

  const updateField = (updatedField: FormField) => {
    setFields(fields.map(f => f.field_id === updatedField.field_id ? updatedField : f));
  };

  const removeField = (fieldId: string) => {
    setFields(fields.filter(f => f.field_id !== fieldId));
  };
  
  const moveField = (fieldId: string, direction: 'up' | 'down') => {
      const index = fields.findIndex(f => f.field_id === fieldId);
      if (index === -1) return;
      const newIndex = direction === 'up' ? index - 1 : index + 1;
      if (newIndex < 0 || newIndex >= fields.length) return;
      const newFields = [...fields];
      [newFields[index], newFields[newIndex]] = [newFields[newIndex], newFields[index]];
      setFields(newFields);
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const payload = {
      title,
      description,
      context_id: contextId,
      status,
      fields: fields.map(f => ({ ...f, options: f.field_type === 'select' ? f.options : [] })),
    };
    try {
      await api.put(`/forms-management/templates/${id}`, payload);
      router.push('/admin/forms');
    } catch (error) {
      console.error('Failed to update form template:', error);
      alert('Failed to update template.');
    }
  };

  if (loading) return <p>Loading form builder...</p>;

  return (
    <div>
      <h1 className="text-3xl font-bold mb-4">Edit Form Template</h1>
      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="p-6 bg-white rounded-lg shadow-md">
          <h2 className="text-xl font-bold mb-4 border-b pb-2">Form Details</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block font-bold mb-1">Title</label>
              <input type="text" value={title} onChange={(e) => setTitle(e.target.value)} className="w-full p-2 border rounded" required />
            </div>
            <div>
              <label className="block font-bold mb-1">Context</label>
              <select value={contextId} onChange={(e) => setContextId(e.target.value)} className="w-full p-2 border rounded" required>
                {contexts.map(c => <option key={c.id} value={c.id}>{c.title}</option>)}
              </select>
            </div>
          </div>
          <div className="mt-4">
            <label className="block font-bold mb-1">Description</label>
            <textarea value={description} onChange={(e) => setDescription(e.target.value)} className="w-full p-2 border rounded" rows={3}/>
          </div>
           <div className="mt-4">
              <label className="block font-bold mb-1">Status</label>
              <select value={status} onChange={(e) => setStatus(e.target.value as FormTemplate['status'])} className="w-full p-2 border rounded">
                <option value="draft">Draft</option>
                <option value="active">Active</option>
                <option value="archived">Archived</option>
              </select>
            </div>
        </div>

        <div className="p-6 bg-white rounded-lg shadow-md">
          <h2 className="text-xl font-bold mb-4 border-b pb-2">Form Fields</h2>
          <div className="space-y-4">
            {fields.map((field, index) => (
              <FieldEditor 
                key={field.field_id} 
                field={field} 
                updateField={updateField} 
                removeField={removeField}
                moveFieldUp={() => moveField(field.field_id, 'up')}
                moveFieldDown={() => moveField(field.field_id, 'down')}
                isFirst={index === 0}
                isLast={index === fields.length - 1}
              />
            ))}
          </div>
          <button type="button" onClick={addField} className="mt-4 bg-gray-200 py-2 px-4 rounded hover:bg-gray-300 font-semibold">
            + Add Field
          </button>
        </div>

        <div className="flex justify-end">
            <button type="submit" className="bg-blue-500 text-white py-2 px-4 rounded hover:bg-blue-600 font-bold">
                Save Changes
            </button>
        </div>
      </form>
    </div>
  );
}

export default withAdminAuth(EditFormPage);