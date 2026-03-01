import { useState, useEffect } from 'react';
import { useRiderApplications, useRiderApplicationCount, useReviewApplication } from '../api/client';
import DataTable from '../components/ui/DataTable';
import Badge from '../components/ui/Badge';
import Spinner from '../components/ui/Spinner';
import { X, CheckCircle, XCircle, Eye, ZoomIn, ChevronLeft } from 'lucide-react';

const STATUS_TABS = ['All', 'PENDING', 'APPROVED', 'REJECTED'];

export default function RiderApplications() {
    const [activeTab, setActiveTab] = useState('PENDING');
    const [selectedApp, setSelectedApp] = useState(null);
    const [adminNote, setAdminNote] = useState('');
    const [lightboxUrl, setLightboxUrl] = useState(null);

    const statusFilter = activeTab === 'All' ? undefined : activeTab;
    const { data: applications, isLoading, refetch } = useRiderApplications(statusFilter);
    const { data: pendingCount } = useRiderApplicationCount('PENDING');
    const reviewMutation = useReviewApplication();

    // Poll every 30s
    useEffect(() => {
        const interval = setInterval(() => refetch(), 30000);
        return () => clearInterval(interval);
    }, [refetch]);

    const handleReview = async (action) => {
        if (!selectedApp) return;
        try {
            await reviewMutation.mutateAsync({
                applicationId: selectedApp.id,
                action,
                admin_note: adminNote || undefined,
                reviewed_by: 'admin',
            });
            setSelectedApp(null);
            setAdminNote('');
            refetch();
        } catch (e) {
            alert('Review failed: ' + e.message);
        }
    };

    const columns = [
        {
            key: 'full_name', label: 'Name',
            render: (v) => <span className="font-medium">{v}</span>,
        },
        { key: 'phone', label: 'Phone' },
        {
            key: 'vehicle', label: 'Vehicle',
            render: (v) => <Badge value={v} />,
        },
        {
            key: 'created_at', label: 'Submitted',
            render: (v) => <span className="text-xs text-gray-500">{new Date(v).toLocaleDateString()}</span>,
        },
        {
            key: 'status', label: 'Status',
            render: (v) => {
                const styles = {
                    PENDING: 'bg-yellow-100 text-yellow-700',
                    APPROVED: 'bg-green-100 text-green-700',
                    REJECTED: 'bg-red-100 text-red-700',
                };
                return (
                    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${styles[v] || 'bg-gray-100 text-gray-600'}`}>
                        {v}
                    </span>
                );
            },
        },
        {
            key: 'id', label: 'Actions', sortable: false,
            render: (_, row) => (
                <button
                    onClick={(e) => { e.stopPropagation(); setSelectedApp(row); setAdminNote(''); }}
                    className="flex items-center gap-1 px-2 py-1 text-xs bg-blue-50 text-blue-600 rounded hover:bg-blue-100"
                >
                    <Eye size={14} /> Review
                </button>
            ),
        },
    ];

    if (isLoading) return <Spinner />;

    return (
        <div className="space-y-4">
            {/* Header */}
            <div className="flex items-center justify-between">
                <h1 className="text-xl font-bold text-gray-800">
                    🆔 Rider Applications
                    {pendingCount?.count > 0 && (
                        <span className="ml-2 inline-flex items-center justify-center w-6 h-6 text-xs font-bold text-white bg-red-500 rounded-full">
                            {pendingCount.count}
                        </span>
                    )}
                </h1>
            </div>

            {/* Tabs */}
            <div className="flex gap-1 bg-white rounded-lg border border-gray-200 p-1 w-fit">
                {STATUS_TABS.map(tab => (
                    <button
                        key={tab}
                        onClick={() => setActiveTab(tab)}
                        className={`px-4 py-1.5 text-sm rounded ${activeTab === tab
                            ? 'bg-blue-600 text-white'
                            : 'text-gray-600 hover:bg-gray-50'
                        }`}
                    >
                        {tab === 'All' ? 'All' : tab.charAt(0) + tab.slice(1).toLowerCase()}
                    </button>
                ))}
            </div>

            {/* Table */}
            <div className="bg-white rounded-lg border border-gray-200">
                <DataTable
                    columns={columns}
                    data={applications || []}
                    emptyMessage="No applications found"
                    onRowClick={(row) => { setSelectedApp(row); setAdminNote(''); }}
                />
            </div>

            {/* Slide-Over Review Panel */}
            {selectedApp && (
                <div className="fixed inset-0 z-50 flex justify-end">
                    <div className="absolute inset-0 bg-black/30" onClick={() => setSelectedApp(null)} />
                    <div className="relative w-[520px] bg-white h-full shadow-xl overflow-y-auto">
                        {/* Header */}
                        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between z-10">
                            <div className="flex items-center gap-2">
                                <button onClick={() => setSelectedApp(null)} className="text-gray-400 hover:text-gray-600">
                                    <ChevronLeft size={20} />
                                </button>
                                <h2 className="text-lg font-semibold text-gray-800">Review Application</h2>
                            </div>
                            <button onClick={() => setSelectedApp(null)} className="text-gray-400 hover:text-gray-600">
                                <X size={18} />
                            </button>
                        </div>

                        {/* Content */}
                        <div className="p-6 space-y-6">
                            {/* Status Badge */}
                            <div className="flex items-center gap-2">
                                <span className="text-sm text-gray-500">Status:</span>
                                <Badge value={selectedApp.status} />
                            </div>

                            {/* Personal Info */}
                            <div className="space-y-3">
                                <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider">Personal Info</h3>
                                <div className="grid grid-cols-2 gap-3">
                                    <InfoField label="Full Name" value={selectedApp.full_name} />
                                    <InfoField label="Phone" value={selectedApp.phone} />
                                    <InfoField label="Email" value={selectedApp.email || 'Not provided'} />
                                    <InfoField label="Telegram ID" value={selectedApp.telegram_id} />
                                </div>
                            </div>

                            {/* Vehicle Info */}
                            <div className="space-y-3">
                                <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider">Vehicle Info</h3>
                                <div className="grid grid-cols-2 gap-3">
                                    <InfoField label="Type" value={selectedApp.vehicle?.replace(/_/g, ' ')} />
                                    <InfoField label="Registration" value={selectedApp.vehicle_reg || 'Not provided'} />
                                </div>
                            </div>

                            {/* Documents */}
                            <div className="space-y-3">
                                <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider">Documents</h3>
                                <div className="space-y-2">
                                    <DocPreview
                                        label="Driving License"
                                        appId={selectedApp.id}
                                        docType="license"
                                        hasDoc={!!selectedApp.license_file_id}
                                        onZoom={setLightboxUrl}
                                    />
                                    <DocPreview
                                        label="Aadhar Card"
                                        appId={selectedApp.id}
                                        docType="aadhar"
                                        hasDoc={!!selectedApp.aadhar_file_id}
                                        onZoom={setLightboxUrl}
                                    />
                                </div>
                            </div>

                            {/* Preferred Hub */}
                            <div className="space-y-3">
                                <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider">Preferences</h3>
                                <InfoField label="Preferred Hub" value={selectedApp.preferred_warehouse_id || 'No preference'} />
                            </div>

                            {/* Review Actions — only for PENDING */}
                            {selectedApp.status === 'PENDING' && (
                                <div className="space-y-3 pt-4 border-t border-gray-200">
                                    <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider">Admin Review</h3>
                                    <textarea
                                        value={adminNote}
                                        onChange={(e) => setAdminNote(e.target.value)}
                                        placeholder="Admin note (recommended for rejections)..."
                                        rows={3}
                                        className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500"
                                    />
                                    <div className="flex gap-3">
                                        <button
                                            onClick={() => handleReview('APPROVE')}
                                            disabled={reviewMutation.isPending}
                                            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 font-medium"
                                        >
                                            <CheckCircle size={18} />
                                            {reviewMutation.isPending ? 'Processing...' : 'Approve Rider'}
                                        </button>
                                        <button
                                            onClick={() => handleReview('REJECT')}
                                            disabled={reviewMutation.isPending}
                                            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 font-medium"
                                        >
                                            <XCircle size={18} />
                                            {reviewMutation.isPending ? 'Processing...' : 'Reject Application'}
                                        </button>
                                    </div>
                                </div>
                            )}

                            {/* Already reviewed info */}
                            {selectedApp.status !== 'PENDING' && selectedApp.reviewed_by && (
                                <div className="space-y-3 pt-4 border-t border-gray-200">
                                    <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider">Review Info</h3>
                                    <InfoField label="Reviewed By" value={selectedApp.reviewed_by} />
                                    <InfoField label="Reviewed At" value={selectedApp.reviewed_at ? new Date(selectedApp.reviewed_at).toLocaleString() : '—'} />
                                    {selectedApp.admin_note && (
                                        <InfoField label="Admin Note" value={selectedApp.admin_note} />
                                    )}
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Lightbox */}
            {lightboxUrl && (
                <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/80" onClick={() => setLightboxUrl(null)}>
                    <button onClick={() => setLightboxUrl(null)} className="absolute top-4 right-4 text-white hover:text-gray-300">
                        <X size={24} />
                    </button>
                    <img src={lightboxUrl} alt="Document" className="max-w-[90vw] max-h-[90vh] object-contain rounded-lg" />
                </div>
            )}
        </div>
    );
}

function InfoField({ label, value }) {
    return (
        <div>
            <span className="text-xs text-gray-400">{label}</span>
            <p className="text-sm text-gray-800 font-medium mt-0.5">{value || '—'}</p>
        </div>
    );
}

function DocPreview({ label, appId, docType, hasDoc, onZoom }) {
    // Use the API proxy endpoint so the Telegram bot token never hits the browser
    const imgSrc = hasDoc ? `/api/rider-applications/${appId}/file/${docType}` : null;

    return (
        <div className="flex items-center justify-between bg-gray-50 rounded-lg p-3">
            <div>
                <span className="text-sm font-medium text-gray-700">{label}</span>
                <span className={`ml-2 text-xs ${hasDoc ? 'text-green-600' : 'text-gray-400'}`}>
                    {hasDoc ? '✅ Uploaded' : 'Not provided'}
                </span>
            </div>
            {imgSrc && (
                <button
                    onClick={() => onZoom(imgSrc)}
                    className="flex items-center gap-1 px-2 py-1 text-xs bg-blue-50 text-blue-600 rounded hover:bg-blue-100"
                >
                    <ZoomIn size={14} /> View
                </button>
            )}
        </div>
    );
}
