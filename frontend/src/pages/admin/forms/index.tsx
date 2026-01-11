import { useState, useEffect } from 'react';
import api from '@/lib/api';
import withAdminAuth from '@/components/withAdminAuth';
import { FormTemplate } from '@/types';
import Link from 'next/link';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/badge';
import { motion } from 'framer-motion';

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

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-pulse text-muted-foreground">Loading templates...</div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto py-8 px-4">
      {/* Header */}
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Form Templates</h1>
          <p className="text-muted-foreground mt-1">Create and manage your form templates</p>
        </div>
        <Link href="/admin/forms/new">
          <Button className="rounded-full px-6">
            + Create Template
          </Button>
        </Link>
      </div>

      {/* Templates Grid */}
      {templates.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {templates.map((template, index) => (
            <motion.div
              key={template.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
            >
              <Card className="group hover:shadow-lg transition-all duration-300 hover:-translate-y-1 cursor-pointer border-0 shadow-md">
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between">
                    <CardTitle className="text-lg font-semibold group-hover:text-primary transition-colors">
                      {template.title}
                    </CardTitle>
                    <Badge
                      variant={template.status === 'active' ? 'default' : 'secondary'}
                      className="capitalize rounded-full"
                    >
                      {template.status}
                    </Badge>
                  </div>
                  <CardDescription className="line-clamp-2">
                    {template.description || 'No description provided'}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">
                      {template.fields.length} field{template.fields.length !== 1 ? 's' : ''}
                    </span>
                    <Link
                      href={`/admin/forms/${template.id}/edit`}
                      className="text-primary hover:underline font-medium"
                    >
                      Edit →
                    </Link>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      ) : (
        <Card className="border-dashed border-2 bg-muted/30">
          <CardContent className="flex flex-col items-center justify-center py-16">
            <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mb-4">
              <svg className="w-8 h-8 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold mb-2">No templates yet</h3>
            <p className="text-muted-foreground text-center mb-6">
              Create your first form template to get started
            </p>
            <Link href="/admin/forms/new">
              <Button className="rounded-full">Create Template</Button>
            </Link>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export default withAdminAuth(FormsPage);