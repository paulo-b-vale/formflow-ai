import { FormField } from '@/types';
import { Card, CardContent } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/Button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { motion } from 'framer-motion';
import { ChevronUpIcon, ChevronDownIcon, TrashIcon } from '@heroicons/react/24/outline';

interface FieldEditorProps {
  field: FormField;
  updateField: (field: FormField) => void;
  removeField: (fieldId: string) => void;
  moveFieldUp: (fieldId: string) => void;
  moveFieldDown: (fieldId: string) => void;
  isFirst: boolean;
  isLast: boolean;
}

const FieldEditor = ({
  field,
  updateField,
  removeField,
  moveFieldUp,
  moveFieldDown,
  isFirst,
  isLast,
}: FieldEditorProps) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
    >
      <Card className="border border-border/50 shadow-sm hover:shadow-md transition-shadow group">
        <CardContent className="p-5">
          {/* Header with reorder and delete buttons */}
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-1">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => moveFieldUp(field.field_id)}
                disabled={isFirst}
                className="h-8 w-8 p-0 opacity-50 hover:opacity-100 disabled:opacity-20"
              >
                <ChevronUpIcon className="h-4 w-4" />
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => moveFieldDown(field.field_id)}
                disabled={isLast}
                className="h-8 w-8 p-0 opacity-50 hover:opacity-100 disabled:opacity-20"
              >
                <ChevronDownIcon className="h-4 w-4" />
              </Button>
            </div>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => removeField(field.field_id)}
              className="h-8 w-8 p-0 text-destructive opacity-50 hover:opacity-100 hover:bg-destructive/10"
            >
              <TrashIcon className="h-4 w-4" />
            </Button>
          </div>

          {/* Field Label */}
          <div className="space-y-2 mb-4">
            <Label>Field Label</Label>
            <Input
              placeholder="e.g., Patient Name, Email Address"
              value={field.label}
              onChange={(e) => updateField({ ...field, label: e.target.value })}
              className="h-11"
            />
          </div>

          {/* Description */}
          <div className="space-y-2 mb-4">
            <Label>Help Text (optional)</Label>
            <Textarea
              placeholder="Add a description to help users understand what to enter..."
              value={field.description || ''}
              onChange={(e) => updateField({ ...field, description: e.target.value })}
              className="min-h-[80px] resize-none text-sm"
            />
          </div>

          {/* Field Type and Required */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Field Type</Label>
              <Select
                value={field.field_type}
                onValueChange={(value) =>
                  updateField({ ...field, field_type: value as FormField['field_type'] })
                }
              >
                <SelectTrigger className="h-11">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="text">Text</SelectItem>
                  <SelectItem value="textarea">Text Area</SelectItem>
                  <SelectItem value="number">Number</SelectItem>
                  <SelectItem value="date">Date</SelectItem>
                  <SelectItem value="boolean">Yes/No</SelectItem>
                  <SelectItem value="select">Dropdown</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-end">
              <label className="flex items-center gap-3 cursor-pointer py-3">
                <input
                  type="checkbox"
                  checked={field.required}
                  onChange={(e) => updateField({ ...field, required: e.target.checked })}
                  className="h-5 w-5 rounded border-gray-300 text-primary focus:ring-primary"
                />
                <span className="text-sm font-medium">Required field</span>
              </label>
            </div>
          </div>

          {/* Options for Select type */}
          {field.field_type === 'select' && (
            <div className="space-y-2 mt-4 pt-4 border-t">
              <Label>Dropdown Options</Label>
              <Textarea
                placeholder="Enter options separated by commas (e.g., Option A, Option B, Option C)"
                value={field.options?.join(', ') || ''}
                onChange={(e) =>
                  updateField({
                    ...field,
                    options: e.target.value
                      .split(',')
                      .map((s) => s.trim())
                      .filter(Boolean),
                  })
                }
                className="min-h-[60px] resize-none text-sm"
              />
            </div>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
};

export default FieldEditor;
