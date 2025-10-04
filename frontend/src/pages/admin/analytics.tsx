import { useState, useEffect } from 'react';
import withAdminAuth from '@/components/withAdminAuth';
import api from '@/lib/api';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

interface GeneralStat {
  total_chats: number;
  total_forms_filled: number;
  total_users: number;
  active_users_today: number;
}
interface CostDataPoint { 
  timestamp: string; 
  cost: number; 
  model_name?: string; 
}
interface TokenDataPoint { 
  timestamp: string; 
  tokens_used: number; 
  model_name?: string; 
}
interface AnalyticsData {
  general_stats: GeneralStat;
  cost_analytics: {
    total_cost: string; // Actually a Decimal in backend, but comes as string
    cost_by_model: Record<string, unknown>;
    daily_costs: CostDataPoint[];
  };
  token_analytics: {
    total_tokens: number;
    tokens_by_model: Record<string, unknown>;
    daily_tokens: TokenDataPoint[];
  };
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#AF19FF', '#FF1943'];

const StatCard = ({ title, value }: { title: string; value: string | number }) => (
    <div className="bg-white p-6 rounded-lg shadow-md">
        <h3 className="text-gray-500 text-sm font-semibold uppercase">{title}</h3>
        <p className="text-3xl font-bold mt-2">{value}</p>
    </div>
);

function AnalyticsPage() {
    const [data, setData] = useState<AnalyticsData | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        api.get('/analytics/dashboard')
            .then(res => setData(res.data))
            .catch(err => console.error("Failed to fetch analytics", err))
            .finally(() => setLoading(false));
    }, []);

    if (loading) return <p>Loading analytics dashboard...</p>;
    if (!data) return <p>Could not load analytics data.</p>;

    return (
        <div>
            <h1 className="text-3xl font-bold mb-6">Analytics Dashboard</h1>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                <StatCard title="Total Chats" value={data.general_stats.total_chats} />
                <StatCard title="Total Forms Filled" value={data.general_stats.total_forms_filled} />
                <StatCard title="Total Users" value={data.general_stats.total_users} />
                <StatCard title="Active Users Today" value={data.general_stats.active_users_today} />
            </div>
            
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <div className="bg-white p-6 rounded-lg shadow-md">
                    <h2 className="text-xl font-bold mb-4">Total Cost</h2>
                    <p className="text-3xl font-bold text-green-600">${data.cost_analytics.total_cost}</p>
                </div>

                <div className="bg-white p-6 rounded-lg shadow-md">
                    <h2 className="text-xl font-bold mb-4">Total Tokens Used</h2>
                    <p className="text-3xl font-bold text-blue-600">{data.token_analytics.total_tokens.toLocaleString()}</p>
                </div>
            </div>

            {/* Daily costs chart if data exists */}
            {data.cost_analytics.daily_costs.length > 0 && (
                <div className="bg-white p-6 rounded-lg shadow-md mt-8">
                    <h2 className="text-xl font-bold mb-4">Daily Cost Trend</h2>
                    <ResponsiveContainer width="100%" height={300}>
                        <BarChart data={data.cost_analytics.daily_costs}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey="timestamp" />
                            <YAxis tickFormatter={(tick) => `${tick.toFixed(4)}`} />
                            <Tooltip formatter={(value: number) => `${value.toFixed(6)}`} />
                            <Legend />
                            <Bar dataKey="cost" fill="#8884d8" name="Cost (USD)" />
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            )}

            {/* Daily tokens chart if data exists */}
            {data.token_analytics.daily_tokens.length > 0 && (
                <div className="bg-white p-6 rounded-lg shadow-md mt-8">
                    <h2 className="text-xl font-bold mb-4">Daily Token Usage</h2>
                    <ResponsiveContainer width="100%" height={300}>
                        <BarChart data={data.token_analytics.daily_tokens}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey="timestamp" />
                            <YAxis tickFormatter={(tick) => tick.toLocaleString()} />
                            <Tooltip formatter={(value: number) => `${value.toLocaleString()} tokens`} />
                            <Legend />
                            <Bar dataKey="tokens_used" fill="#00C49F" name="Tokens Used" />
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            )}
        </div>
    );
}

export default withAdminAuth(AnalyticsPage);