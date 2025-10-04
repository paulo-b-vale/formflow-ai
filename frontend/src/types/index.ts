export interface User {
  id: string;
  name: string;
  email: string;
  role: 'user' | 'professional' | 'admin';
  is_active: boolean;
}

export interface WorkContext {
  id: string;
  title: string;
  description: string;
  context_type: string;
  created_by: string;
  assigned_users: string[];
  is_active: boolean;
}

export interface FormField {
  field_id: string;
  label: string;
  field_type: 'text' | 'textarea' | 'number' | 'date' | 'boolean' | 'select';
  required: boolean;
  description?: string;
  options?: string[];
  placeholder?: string;
}

export interface FormTemplate {
  id: string;
  title: string;
  description: string;
  context_id: string;
  fields: FormField[];
  status: 'draft' | 'active' | 'archived';
}

export interface FormResponse {
  id: string;
  form_template_id: string;
  respondent_id: string;
  respondent_name: string;
  responses: Record<string, any>;
  status: 'incomplete' | 'complete' | 'pending_review' | 'approved' | 'rejected';
  submitted_at: string;
  reviewed_at?: string;
  reviewed_by?: string;
  review_notes?: string;
}