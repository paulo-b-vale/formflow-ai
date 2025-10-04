import { useState } from 'react';
import api from '../../lib/api';
import { FormResponse } from '../../types';

interface ReviewPanelProps {
    response: FormResponse;
    onReviewSuccess: () => void;
}

export default function ReviewPanel({ response, onReviewSuccess }: ReviewPanelProps) {
    const [status, setStatus] = useState<'approved' | 'rejected' | ''>('');
    const [notes, setNotes] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);

    const handleSubmitReview = async () => {
        if (!status) {
            alert('Please select a status (Approve or Reject).');
            return;
        }
        setIsSubmitting(true);
        try {
            await api.put(`/forms-management/responses/${response.id}/review`, {
                status,
                review_notes: notes,
            });
            onReviewSuccess();
        } catch (error) {
            console.error('Failed to submit review:', error);
            alert('Failed to submit review.');
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="bg-white p-6 rounded shadow-md">
            <h2 className="text-xl font-bold mb-4">Review Panel</h2>
            {response.status === 'approved' || response.status === 'rejected' ? (
                <div>
                    <p><strong>Status:</strong> <span className="capitalize font-semibold">{response.status}</span></p>
                    <p><strong>Reviewed At:</strong> {new Date(response.reviewed_at!).toLocaleString()}</p>
                    {response.review_notes && <p className="mt-2"><strong>Notes:</strong> {response.review_notes}</p>}
                </div>
            ) : (
                <div className="space-y-4">
                    <div>
                        <label className="block font-bold mb-1">Status</label>
                        <select value={status} onChange={(e) => setStatus(e.target.value as any)} className="w-full p-2 border rounded">
                            <option value="" disabled>Select status...</option>
                            <option value="approved">Approve</option>
                            <option value="rejected">Reject</option>
                        </select>
                    </div>
                    <div>
                        <label className="block font-bold mb-1">Review Notes (Optional)</label>
                        <textarea
                            value={notes}
                            onChange={(e) => setNotes(e.target.value)}
                            className="w-full p-2 border rounded"
                            rows={4}
                            placeholder="Add feedback or comments here..."
                        />
                    </div>
                    <button
                        onClick={handleSubmitReview}
                        disabled={isSubmitting}
                        className="w-full bg-blue-500 text-white p-2 rounded hover:bg-blue-600 disabled:bg-gray-400"
                    >
                        {isSubmitting ? 'Submitting...' : 'Submit Review'}
                    </button>
                </div>
            )}
        </div>
    );
}