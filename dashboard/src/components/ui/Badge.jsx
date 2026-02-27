const variants = {
    // Order statuses
    ORDER_PLACED: 'bg-gray-100 text-gray-700',
    PAYMENT_CONFIRMED: 'bg-blue-100 text-blue-700',
    PICKUP_SCHEDULED: 'bg-blue-100 text-blue-700',
    PICKUP_RIDER_ASSIGNED: 'bg-indigo-100 text-indigo-700',
    PICKUP_EN_ROUTE: 'bg-indigo-100 text-indigo-700',
    PICKED_UP: 'bg-yellow-100 text-yellow-700',
    IN_TRANSIT_TO_WAREHOUSE: 'bg-yellow-100 text-yellow-700',
    AT_WAREHOUSE: 'bg-purple-100 text-purple-700',
    ROUTE_OPTIMIZED: 'bg-purple-100 text-purple-700',
    DELIVERY_RIDER_ASSIGNED: 'bg-cyan-100 text-cyan-700',
    OUT_FOR_DELIVERY: 'bg-orange-100 text-orange-700',
    DELIVERED: 'bg-green-100 text-green-700',
    COMPLETED: 'bg-green-100 text-green-700',
    CANCELLED: 'bg-red-100 text-red-700',
    REFUNDED: 'bg-red-100 text-red-700',
    // Rider statuses
    ON_DUTY: 'bg-green-100 text-green-700',
    OFF_DUTY: 'bg-gray-100 text-gray-600',
    ON_DELIVERY: 'bg-orange-100 text-orange-700',
    ON_PICKUP: 'bg-blue-100 text-blue-700',
    // Payment
    PAID: 'bg-green-100 text-green-700',
    PENDING: 'bg-yellow-100 text-yellow-700',
    FAILED: 'bg-red-100 text-red-700',
    COD: 'bg-amber-100 text-amber-700',
    CARD: 'bg-blue-100 text-blue-700',
    UPI: 'bg-purple-100 text-purple-700',
    // Severity
    INFO: 'bg-blue-100 text-blue-700',
    WARNING: 'bg-yellow-100 text-yellow-700',
    CRITICAL: 'bg-red-100 text-red-700',
};

export default function Badge({ value, className = '' }) {
    if (!value) return null;
    const style = variants[value] || 'bg-gray-100 text-gray-600';
    const label = value.replace(/_/g, ' ');
    return (
        <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${style} ${className}`}>
            {label}
        </span>
    );
}
