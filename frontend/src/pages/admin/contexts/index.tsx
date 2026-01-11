import { useState, useEffect } from 'react';
import api from '@/lib/api';
import withAdminAuth from '@/components/withAdminAuth';
import { WorkContext } from '@/types';
import Link from 'next/link';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/badge';
import { motion } from 'framer-motion';

function ContextsPage() {
    const [contexts, setContexts] = useState<WorkContext[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchContexts = async () => {
            try {
                const response = await api.get('/forms-management/contexts');
                setContexts(response.data);
            } catch (error) {
                console.error('Failed to fetch contexts:', error);
            } finally {
                setLoading(false);
            }
        };
        fetchContexts();
    }, []);

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-[400px]">
                <div className="animate-pulse text-muted-foreground">Loading contexts...</div>
            </div>
        );
    }

    return (
        <div className="max-w-6xl mx-auto py-8 px-4">
            {/* Header */}
            <div className="flex justify-between items-center mb-8">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight text-foreground">Work Contexts</h1>
                    <p className="text-muted-foreground mt-1">Manage departmental and project environments</p>
                </div>
                <Link href="/admin/contexts/new">
                    <Button className="rounded-full px-6 shadow-md hover:shadow-lg transition-all">
                        + Create Context
                    </Button>
                </Link>
            </div>

            {/* Contexts Grid */}
            {contexts.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {contexts.map((context, index) => (
                        <motion.div
                            key={context.id}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: index * 0.1 }}
                        >
                            <Card className="group hover:shadow-xl transition-all duration-300 hover:-translate-y-1 cursor-pointer border-0 shadow-md bg-card">
                                <CardHeader className="pb-3 border-b border-border/50">
                                    <div className="flex items-start justify-between">
                                        <CardTitle className="text-lg font-semibold group-hover:text-primary transition-colors">
                                            {context.title}
                                        </CardTitle>
                                        <Badge
                                            variant={context.is_active ? 'default' : 'secondary'}
                                            className="capitalize rounded-full px-3 py-0.5 text-[10px]"
                                        >
                                            {context.is_active ? 'Active' : 'Inactive'}
                                        </Badge>
                                    </div>
                                    <CardDescription className="line-clamp-2 mt-2 text-sm">
                                        {context.description || 'No description provided'}
                                    </CardDescription>
                                </CardHeader>
                                <CardContent className="pt-4">
                                    <div className="flex flex-col gap-3">
                                        <div className="flex items-center justify-between text-xs text-muted-foreground">
                                            <div className="flex items-center gap-1.5">
                                                <span className="w-2 h-2 rounded-full bg-purple-400" />
                                                <span className="capitalize">{context.context_type || 'General'}</span>
                                            </div>
                                            <div className="flex -space-x-2">
                                                {/* Representation of assigned users */}
                                                {context.assigned_users && context.assigned_users.length > 0 ? (
                                                    <>
                                                        {context.assigned_users.slice(0, 3).map((_, i) => (
                                                            <div key={i} className="w-6 h-6 rounded-full border-2 border-background bg-muted flex items-center justify-center text-[10px] font-bold">
                                                                {String.fromCharCode(65 + i)}
                                                            </div>
                                                        ))}
                                                        {context.assigned_users.length > 3 && (
                                                            <div className="w-6 h-6 rounded-full border-2 border-background bg-muted flex items-center justify-center text-[8px] font-medium">
                                                                +{context.assigned_users.length - 3}
                                                            </div>
                                                        )}
                                                    </>
                                                ) : (
                                                    <span className="text-[10px]">No users</span>
                                                )}
                                            </div>
                                        </div>

                                        <div className="flex justify-end pt-2">
                                            <Link
                                                href={`/admin/contexts/${context.id}/edit`}
                                                className="text-primary hover:text-primary/80 text-sm font-medium flex items-center gap-1 group/link"
                                            >
                                                Edit Context
                                                <span className="group-hover/link:translate-x-1 transition-transform">→</span>
                                            </Link>
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>
                        </motion.div>
                    ))}
                </div>
            ) : (
                <Card className="border-dashed border-2 bg-muted/20 border-border">
                    <CardContent className="flex flex-col items-center justify-center py-20">
                        <div className="w-20 h-20 rounded-full bg-primary/5 flex items-center justify-center mb-6">
                            <svg className="w-10 h-10 text-primary opacity-60" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                            </svg>
                        </div>
                        <h3 className="text-xl font-bold mb-2">No contexts found</h3>
                        <p className="text-muted-foreground text-center mb-8 max-w-xs">
                            Contexts allow you to group forms and users into specific categories or departments.
                        </p>
                        <Link href="/admin/contexts/new">
                            <Button className="rounded-full px-8 shadow-lg">Create Your First Context</Button>
                        </Link>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}

export default withAdminAuth(ContextsPage);
