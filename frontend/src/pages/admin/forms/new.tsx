import { useState, useEffect, FormEvent } from 'react';
import api from '@/lib/api';
import withAdminAuth from '@/components/withAdminAuth';
import { WorkContext, FormField } from '@/types';
import { useRouter } from 'next/router';
import { v4 as uuidv4 } from 'uuid';
import FieldEditor from '@/components/forms/FieldEditor';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

function NewFormPage() {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [contextId, setContextId] = useState('');
  const [fields, setFields] = useState<FormField[]>([]);
  const [contexts, setContexts] = useState<WorkContext[]>([]);
  const router = useRouter();

  useEffect(() => {
    api.get('/forms-management/contexts').then((res) => {
      const activeContexts = res.data.filter((c: WorkContext) => c.is_active);
      setContexts(activeContexts);
      if (activeContexts.length > 0) {
        setContextId(activeContexts[0].id);
      }
    });
  }, []);

  const addField = () => {
    setFields([
      ...fields,
      {
        field_id: uuidv4(),
        label: '',
        field_type: 'text',
        required: false,
        description: '',
        options: [],
      },
    ]);
  };

  const updateField = (updatedField: FormField) => {
    setFields(fields.map((f) => (f.field_id === updatedField.field_id ? updatedField : f)));
  };

  const removeField = (fieldId: string) => {
    setFields(fields.filter((f) => f.field_id !== fieldId));
  };

  const moveField = (fieldId: string, direction: 'up' | 'down') => {
    const index = fields.findIndex((f) => f.field_id === fieldId);
    if (index === -1) return;

    const newIndex = direction === 'up' ? index - 1 : index + 1;
    if (newIndex < 0 || newIndex >= fields.length) return;

    const newFields = [...fields];
    [newFields[index], newFields[newIndex]] = [newFields[newIndex], newFields[index]];
    setFields(newFields);
  };

  const handleSubmit = async (e: FormEvent, status: 'draft' | 'active') => {
    e.preventDefault();
    if (!contextId) {
      alert('Please select an active context.');
      return;
    }
    const payload = {
      title,
      description,
      context_id: contextId,
      status,
      fields: fields.map((f) => ({ ...f, options: f.field_type === 'select' ? f.options : [] })),
    };
    try {
      await api.post('/forms-management/templates', payload);
      router.push('/admin/forms');
    } catch (error) {
      console.error('Failed to create form template:', error);
      alert('Failed to create template.');
    }
  };

  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight">Create New Template</h1>
        <p className="text-muted-foreground mt-1">Design your form with custom fields</p>
      </div>

      <form className="space-y-8">
        {/* Form Details Card */}
        <Card className="border-0 shadow-md">
          <CardHeader className="pb-4">
            <CardTitle className="text-xl">Form Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <Label htmlFor="title">Title</Label>
                <Input
                  id="title"
                  placeholder="Enter form title"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="h-12"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="context">Context</Label>
                <Select value={contextId} onValueChange={setContextId}>
                  <SelectTrigger className="h-12">
                    <SelectValue placeholder="Select a context" />
                  </SelectTrigger>
                  <SelectContent>
                    {contexts.map((c) => (
                      <SelectItem key={c.id} value={c.id}>
                        {c.title}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                placeholder="Describe what this form is for..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="min-h-[100px] resize-none"
              />
            </div>
          </CardContent>
        </Card>

        {/* Form Fields Card */}
        <Card className="border-0 shadow-md">
          <CardHeader className="pb-4">
            <CardTitle className="text-xl">Form Fields</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {fields.length === 0 ? (
              <div className="text-center py-12 border-2 border-dashed rounded-xl border-muted">
                <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-4">
                  <svg className="w-6 h-6 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                  </svg>
                </div>
                <p className="text-muted-foreground mb-4">No fields added yet</p>
                <Button type="button" onClick={addField} variant="outline" className="rounded-full">
                  Add your first field
                </Button>
              </div>
            ) : (
              <>
                <div className="space-y-3">
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
                <Button
                  type="button"
                  onClick={addField}
                  variant="outline"
                  className="w-full rounded-xl border-dashed"
                >
                  + Add Another Field
                </Button>
              </>
            )}
          </CardContent>
        </Card>

        {/* Action Buttons */}
        <div className="flex justify-end gap-4">
          <Button
            type="button"
            variant="outline"
            onClick={(e) => handleSubmit(e, 'draft')}
            className="rounded-full px-8"
          >
            Save as Draft
          </Button>
          <Button
            type="button"
            onClick={(e) => handleSubmit(e, 'active')}
            className="rounded-full px-8"
          >
            Save & Activate
          </Button>
        </div>
      </form>
    </div>
  );
}

export default withAdminAuth(NewFormPage);