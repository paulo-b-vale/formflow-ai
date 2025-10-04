import { FormField } from '@/types';

interface FieldEditorProps {
  field: FormField;
  updateField: (field: FormField) => void;
  removeField: (fieldId: string) => void;
  moveFieldUp: (fieldId: string) => void;
  moveFieldDown: (fieldId: string) => void;
  isFirst: boolean;
  isLast: boolean;
}

const FieldEditor = ({ field, updateField, removeField, moveFieldUp, moveFieldDown, isFirst, isLast }: FieldEditorProps) => {
  return (
    <div className="p-4 border rounded bg-gray-50 space-y-3 relative">
      <div className="absolute top-2 right-2 flex space-x-1">
        <button type="button" onClick={() => moveFieldUp(field.field_id)} disabled={isFirst} className="p-1 disabled:opacity-30 text-gray-600 hover:text-black">↑</button>
        <button type="button" onClick={() => moveFieldDown(field.field_id)} disabled={isLast} className="p-1 disabled:opacity-30 text-gray-600 hover:text-black">↓</button>
      </div>
      <input
        type="text"
        placeholder="Field Label (e.g., Patient Name)"
        value={field.label}
        onChange={(e) => updateField({ ...field, label: e.target.value })}
        className="w-full p-2 border rounded"
        required
      />
      <textarea
        placeholder="Description (optional help text for the user)"
        value={field.description || ''}
        onChange={(e) => updateField({ ...field, description: e.target.value })}
        className="w-full p-2 border rounded text-sm"
        rows={2}
      />
      <select
        value={field.field_type}
        onChange={(e) => updateField({ ...field, field_type: e.target.value as FormField['field_type'] })}
        className="w-full p-2 border rounded"
      >
        <option value="text">Text</option>
        <option value="textarea">Text Area</option>
        <option value="number">Number</option>
        <option value="date">Date</option>
        <option value="boolean">Yes/No</option>
        <option value="select">Select (Dropdown)</option>
      </select>
      {field.field_type === 'select' && (
        <textarea
          placeholder="Comma-separated options (e.g., Option A,Option B,Option C)"
          value={field.options?.join(',') || ''}
          onChange={(e) => updateField({ ...field, options: e.target.value.split(',').map(s => s.trim()).filter(Boolean) })}
          className="w-full p-2 border rounded"
        />
      )}
      <div className="flex justify-between items-center pt-2">
        <label className="flex items-center space-x-2 cursor-pointer">
          <input
            type="checkbox"
            checked={field.required}
            onChange={(e) => updateField({ ...field, required: e.target.checked })}
            className="h-4 w-4"
          />
          <span>Required Field</span>
        </label>
        <button type="button" onClick={() => removeField(field.field_id)} className="text-red-600 hover:text-red-800 font-semibold">
          Remove
        </button>
      </div>
    </div>
  );
};

export default FieldEditor;
