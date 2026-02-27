import { Loader2 } from 'lucide-react';

export default function Spinner({ className = '' }) {
    return (
        <div className={`flex items-center justify-center py-12 ${className}`}>
            <Loader2 size={24} className="animate-spin text-gray-400" />
        </div>
    );
}
