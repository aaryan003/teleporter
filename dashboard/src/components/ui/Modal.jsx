import { X } from 'lucide-react';

export default function Modal({ open, onClose, title, children, wide = false }) {
    if (!open) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
            <div className="absolute inset-0 bg-black/40" onClick={onClose} />
            <div className={`relative bg-white rounded-lg shadow-lg ${wide ? 'w-[700px]' : 'w-[500px]'} max-h-[85vh] overflow-hidden`}>
                <div className="flex items-center justify-between px-5 py-3 border-b border-gray-200">
                    <h2 className="text-base font-semibold text-gray-800">{title}</h2>
                    <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
                        <X size={18} />
                    </button>
                </div>
                <div className="p-5 overflow-y-auto max-h-[75vh]">
                    {children}
                </div>
            </div>
        </div>
    );
}
