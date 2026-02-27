import { useState } from 'react';
import { useRiders, useFleetSummary, useCreateRider, useUpdateRiderStatus } from '../api/client';
import DataTable from '../components/ui/DataTable';
import Badge from '../components/ui/Badge';
import Modal from '../components/ui/Modal';
import StatCard from '../components/ui/StatCard';
import Spinner from '../components/ui/Spinner';
import { Users, Truck, Package, UserX } from 'lucide-react';

const RIDER_STATUSES = ['ON_DUTY', 'OFF_DUTY', 'ON_DELIVERY', 'ON_PICKUP'];

export default function Fleet() {
    const [statusFilter, setStatusFilter] = useState('');
    const [showAddModal, setShowAddModal] = useState(false);
    const [formData, setFormData] = useState({
        telegram_id: '', employee_id: '', full_name: '', phone: '',
        vehicle: 'BIKE', shift_start: '08:00', shift_end: '20:00', max_capacity: 5,
    });

    const { data: riders, isLoading } = useRiders(statusFilter || undefined);
    const { data: fleet } = useFleetSummary();
    const createMutation = useCreateRider();
    const statusMutation = useUpdateRiderStatus();

    const handleStatusChange = (riderId, newStatus) => {
        statusMutation.mutate({ riderId, status: newStatus });
    };

    const handleCreate = async (e) => {
        e.preventDefault();
        try {
            await createMutation.mutateAsync({
                ...formData,
                telegram_id: parseInt(formData.telegram_id),
                max_capacity: parseInt(formData.max_capacity),
            });
            setShowAddModal(false);
            setFormData({
                telegram_id: '', employee_id: '', full_name: '', phone: '',
                vehicle: 'BIKE', shift_start: '08:00', shift_end: '20:00', max_capacity: 5,
            });
        } catch (e) {
            alert('Failed: ' + e.message);
        }
    };

    const columns = [
        { key: 'employee_id', label: 'ID', render: (v) => <span className="font-mono text-xs">{v}</span> },
        { key: 'full_name', label: 'Name', render: (v) => <span className="font-medium">{v}</span> },
        { key: 'phone', label: 'Phone' },
        { key: 'vehicle', label: 'Vehicle', render: (v) => <Badge value={v} /> },
        { key: 'status', label: 'Status', render: (v) => <Badge value={v} /> },
        {
            key: 'current_load',
            label: 'Load',
            render: (v, row) => <span>{v}/{row.max_capacity}</span>,
        },
        {
            key: 'rating',
            label: 'Rating',
            render: (v) => <span>⭐ {parseFloat(v).toFixed(1)}</span>,
        },
        { key: 'total_deliveries', label: 'Deliveries' },
        {
            key: 'shift_start',
            label: 'Shift',
            render: (v, row) => <span className="text-xs">{v} — {row.shift_end}</span>,
        },
        {
            key: 'id',
            label: 'Actions',
            sortable: false,
            render: (_, row) => (
                <select
                    className="text-xs border border-gray-200 rounded px-1 py-1"
                    value=""
                    onChange={e => handleStatusChange(row.id, e.target.value)}
                >
                    <option value="">Change...</option>
                    {RIDER_STATUSES.map(s => (
                        <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
                    ))}
                </select>
            ),
        },
    ];

    if (isLoading) return <Spinner />;

    return (
        <div className="space-y-4">
            {/* Fleet Summary */}
            {fleet && (
                <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                    <StatCard label="Total Riders" value={fleet.total} icon={Users} color="blue" />
                    <StatCard label="On Duty" value={fleet.on_duty} icon={Users} color="green" />
                    <StatCard label="On Delivery" value={fleet.on_delivery} icon={Truck} color="orange" />
                    <StatCard label="On Pickup" value={fleet.on_pickup} icon={Package} color="blue" />
                    <StatCard label="Off Duty" value={fleet.off_duty} icon={UserX} color="gray" />
                </div>
            )}

            {/* Toolbar */}
            <div className="flex items-center justify-between bg-white rounded-lg border border-gray-200 p-3">
                <div className="flex items-center gap-3">
                    <select
                        value={statusFilter}
                        onChange={e => setStatusFilter(e.target.value)}
                        className="px-3 py-1.5 text-sm border border-gray-200 rounded"
                    >
                        <option value="">All Statuses</option>
                        {RIDER_STATUSES.map(s => (
                            <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
                        ))}
                    </select>
                    <span className="text-xs text-gray-400">{(riders || []).length} riders</span>
                </div>
                <button
                    onClick={() => setShowAddModal(true)}
                    className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
                >
                    + Add Rider
                </button>
            </div>

            {/* Table */}
            <div className="bg-white rounded-lg border border-gray-200">
                <DataTable columns={columns} data={riders || []} emptyMessage="No riders found" />
            </div>

            {/* Add Rider Modal */}
            <Modal open={showAddModal} onClose={() => setShowAddModal(false)} title="Add New Rider">
                <form onSubmit={handleCreate} className="space-y-3">
                    {[
                        { key: 'telegram_id', label: 'Telegram ID', type: 'number', placeholder: '123456789' },
                        { key: 'employee_id', label: 'Employee ID', placeholder: 'EMP-006' },
                        { key: 'full_name', label: 'Full Name', placeholder: 'Rider Name' },
                        { key: 'phone', label: 'Phone', placeholder: '+91 9876543210' },
                    ].map(({ key, label, type, placeholder }) => (
                        <div key={key}>
                            <label className="block text-sm text-gray-600 mb-1">{label}</label>
                            <input
                                type={type || 'text'}
                                value={formData[key]}
                                onChange={e => setFormData(d => ({ ...d, [key]: e.target.value }))}
                                placeholder={placeholder}
                                required
                                className="w-full px-3 py-1.5 text-sm border border-gray-200 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                            />
                        </div>
                    ))}
                    <div>
                        <label className="block text-sm text-gray-600 mb-1">Vehicle</label>
                        <select
                            value={formData.vehicle}
                            onChange={e => setFormData(d => ({ ...d, vehicle: e.target.value }))}
                            className="w-full px-3 py-1.5 text-sm border border-gray-200 rounded"
                        >
                            <option value="BIKE">Bike</option>
                            <option value="AUTO">Auto</option>
                            <option value="VAN">Van</option>
                        </select>
                    </div>
                    <div className="grid grid-cols-3 gap-3">
                        <div>
                            <label className="block text-sm text-gray-600 mb-1">Shift Start</label>
                            <input type="time" value={formData.shift_start} onChange={e => setFormData(d => ({ ...d, shift_start: e.target.value }))} className="w-full px-3 py-1.5 text-sm border border-gray-200 rounded" />
                        </div>
                        <div>
                            <label className="block text-sm text-gray-600 mb-1">Shift End</label>
                            <input type="time" value={formData.shift_end} onChange={e => setFormData(d => ({ ...d, shift_end: e.target.value }))} className="w-full px-3 py-1.5 text-sm border border-gray-200 rounded" />
                        </div>
                        <div>
                            <label className="block text-sm text-gray-600 mb-1">Max Load</label>
                            <input type="number" value={formData.max_capacity} onChange={e => setFormData(d => ({ ...d, max_capacity: e.target.value }))} className="w-full px-3 py-1.5 text-sm border border-gray-200 rounded" />
                        </div>
                    </div>
                    <div className="flex justify-end gap-2 pt-2">
                        <button type="button" onClick={() => setShowAddModal(false)} className="px-3 py-1.5 text-sm text-gray-600 bg-gray-100 rounded hover:bg-gray-200">Cancel</button>
                        <button type="submit" disabled={createMutation.isPending} className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
                            {createMutation.isPending ? 'Creating...' : 'Create Rider'}
                        </button>
                    </div>
                </form>
            </Modal>
        </div>
    );
}
