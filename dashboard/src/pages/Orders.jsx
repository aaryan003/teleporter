import { useState } from 'react';
import { useOrders, useUpdateOrderStatus, useGenerateOTP } from '../api/client';
import DataTable from '../components/ui/DataTable';
import Badge from '../components/ui/Badge';
import Modal from '../components/ui/Modal';
import Spinner from '../components/ui/Spinner';

const ORDER_STATUSES = [
    'ORDER_PLACED', 'PAYMENT_CONFIRMED', 'PICKUP_SCHEDULED', 'PICKUP_RIDER_ASSIGNED',
    'PICKUP_EN_ROUTE', 'PICKED_UP', 'IN_TRANSIT_TO_WAREHOUSE', 'AT_WAREHOUSE',
    'ROUTE_OPTIMIZED', 'DELIVERY_RIDER_ASSIGNED', 'OUT_FOR_DELIVERY',
    'DELIVERED', 'COMPLETED', 'CANCELLED',
];

export default function Orders() {
    const [filter, setFilter] = useState('');
    const [search, setSearch] = useState('');
    const [selectedOrder, setSelectedOrder] = useState(null);
    const [otpResult, setOtpResult] = useState(null);

    const { data: orders, isLoading } = useOrders({ status: filter || undefined });
    const statusMutation = useUpdateOrderStatus();
    const otpMutation = useGenerateOTP();

    const filtered = search
        ? (orders || []).filter(o =>
            o.order_number?.toLowerCase().includes(search.toLowerCase()) ||
            o.pickup_address?.toLowerCase().includes(search.toLowerCase()) ||
            o.drop_address?.toLowerCase().includes(search.toLowerCase())
        )
        : orders || [];

    const handleStatusChange = (orderId, newStatus) => {
        if (window.confirm(`Update status to ${newStatus.replace(/_/g, ' ')}?`)) {
            statusMutation.mutate({ orderId, status: newStatus });
        }
    };

    const handleGenerateOTP = async (orderId, type) => {
        try {
            const result = await otpMutation.mutateAsync({ orderId, otpType: type });
            setOtpResult(result);
        } catch (e) {
            alert('Failed to generate OTP: ' + e.message);
        }
    };

    const columns = [
        {
            key: 'order_number',
            label: 'Order #',
            render: (v) => <span className="font-mono text-xs font-medium">{v}</span>,
        },
        {
            key: 'status',
            label: 'Status',
            render: (v) => <Badge value={v} />,
        },
        {
            key: 'pickup_address',
            label: 'Pickup',
            render: (v) => <span className="truncate max-w-[150px] block text-xs">{v}</span>,
        },
        {
            key: 'drop_address',
            label: 'Drop',
            render: (v) => <span className="truncate max-w-[150px] block text-xs">{v}</span>,
        },
        { key: 'weight', label: 'Weight' },
        { key: 'vehicle', label: 'Vehicle' },
        {
            key: 'total_cost',
            label: 'Cost',
            render: (v) => <span className="font-medium">₹{v}</span>,
        },
        {
            key: 'payment_mode',
            label: 'Pay Mode',
            render: (v) => v ? <Badge value={v} /> : '—',
        },
        {
            key: 'payment',
            label: 'Payment',
            render: (v) => <Badge value={v} />,
        },
        {
            key: 'created_at',
            label: 'Created',
            render: (v) => v ? new Date(v).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) : '—',
        },
        {
            key: 'id',
            label: 'Actions',
            sortable: false,
            render: (_, row) => (
                <div className="flex items-center gap-1">
                    <button
                        onClick={(e) => { e.stopPropagation(); setSelectedOrder(row); }}
                        className="px-2 py-1 text-xs bg-gray-100 rounded hover:bg-gray-200"
                    >
                        View
                    </button>
                    <select
                        className="text-xs border border-gray-200 rounded px-1 py-1"
                        value=""
                        onChange={(e) => { e.stopPropagation(); handleStatusChange(row.id, e.target.value); }}
                    >
                        <option value="">Status...</option>
                        {ORDER_STATUSES.map(s => (
                            <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
                        ))}
                    </select>
                </div>
            ),
        },
    ];

    if (isLoading) return <Spinner />;

    return (
        <div className="space-y-4">
            {/* Filters */}
            <div className="flex items-center gap-3 bg-white rounded-lg border border-gray-200 p-3">
                <input
                    type="text"
                    placeholder="Search orders..."
                    value={search}
                    onChange={e => setSearch(e.target.value)}
                    className="flex-1 px-3 py-1.5 text-sm border border-gray-200 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
                <select
                    value={filter}
                    onChange={e => setFilter(e.target.value)}
                    className="px-3 py-1.5 text-sm border border-gray-200 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                    <option value="">All Statuses</option>
                    {ORDER_STATUSES.map(s => (
                        <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
                    ))}
                </select>
                <span className="text-xs text-gray-400">{filtered.length} orders</span>
            </div>

            {/* Table */}
            <div className="bg-white rounded-lg border border-gray-200">
                <DataTable
                    columns={columns}
                    data={filtered}
                    onRowClick={setSelectedOrder}
                    emptyMessage="No orders found"
                />
            </div>

            {/* Detail Modal */}
            <Modal open={!!selectedOrder} onClose={() => { setSelectedOrder(null); setOtpResult(null); }} title={`Order ${selectedOrder?.order_number}`} wide>
                {selectedOrder && (
                    <div className="space-y-4">
                        <div className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
                            <div><span className="text-gray-500">Status:</span> <Badge value={selectedOrder.status} /></div>
                            <div><span className="text-gray-500">Payment:</span> <Badge value={selectedOrder.payment} /> {selectedOrder.payment_mode && <Badge value={selectedOrder.payment_mode} className="ml-1" />}</div>
                            <div><span className="text-gray-500">Weight:</span> {selectedOrder.weight}</div>
                            <div><span className="text-gray-500">Vehicle:</span> {selectedOrder.vehicle}</div>
                            <div><span className="text-gray-500">Distance:</span> {selectedOrder.distance_km ? `${selectedOrder.distance_km} km` : '—'}</div>
                            <div><span className="text-gray-500">Cost:</span> <span className="font-semibold">₹{selectedOrder.total_cost}</span></div>
                            <div className="col-span-2"><span className="text-gray-500">Pickup:</span> {selectedOrder.pickup_address}</div>
                            <div className="col-span-2"><span className="text-gray-500">Drop:</span> {selectedOrder.drop_address}</div>
                            <div><span className="text-gray-500">Express:</span> {selectedOrder.is_express ? 'Yes' : 'No'}</div>
                            <div><span className="text-gray-500">Created:</span> {new Date(selectedOrder.created_at).toLocaleString('en-IN')}</div>
                            {selectedOrder.delivered_at && <div><span className="text-gray-500">Delivered:</span> {new Date(selectedOrder.delivered_at).toLocaleString('en-IN')}</div>}
                        </div>

                        {/* OTP Actions */}
                        <div className="border-t border-gray-100 pt-3">
                            <h4 className="text-sm font-medium text-gray-700 mb-2">Actions</h4>
                            <div className="flex gap-2">
                                <button
                                    onClick={() => handleGenerateOTP(selectedOrder.id, 'pickup')}
                                    className="px-3 py-1.5 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
                                    disabled={otpMutation.isPending}
                                >
                                    Generate Pickup OTP
                                </button>
                                <button
                                    onClick={() => handleGenerateOTP(selectedOrder.id, 'drop')}
                                    className="px-3 py-1.5 text-xs bg-green-600 text-white rounded hover:bg-green-700"
                                    disabled={otpMutation.isPending}
                                >
                                    Generate Drop OTP
                                </button>
                            </div>
                            {otpResult && (
                                <div className="mt-2 p-2 bg-yellow-50 border border-yellow-200 rounded text-sm">
                                    <strong>{otpResult.otp_type} OTP:</strong> <code className="bg-yellow-100 px-1 rounded">{otpResult.otp}</code>
                                    <span className="text-xs text-gray-500 ml-2">(expires in {otpResult.expires_in_seconds}s)</span>
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </Modal>
        </div>
    );
}
