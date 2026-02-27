export default function Settings() {
    const config = [
        {
            section: 'Business Hours', items: [
                { label: 'Operating Hours', value: '8:00 AM — 8:00 PM' },
                { label: 'Last Pickup Cutoff', value: '6:30 PM' },
                { label: 'After-Hours Policy', value: 'Next-day scheduling only' },
            ]
        },
        {
            section: 'Pricing', items: [
                { label: 'Base Rate', value: '₹10/km' },
                { label: 'Minimum Charge', value: '₹25' },
                { label: 'Express Multiplier', value: '1.8x' },
                { label: 'Next-Day Discount', value: '0.9x' },
                { label: 'Batch Discount', value: '15%' },
            ]
        },
        {
            section: 'Vehicle Multipliers', items: [
                { label: 'Bike (< 5kg)', value: '1.0x' },
                { label: 'Auto (5-20kg)', value: '1.3x' },
                { label: 'Van (> 20kg)', value: '1.6x' },
            ]
        },
        {
            section: 'Surge Pricing', items: [
                { label: 'Threshold Ratio', value: '2.0 (orders/riders)' },
                { label: 'Max Surge', value: '1.6x' },
                { label: 'Rider Surge Share', value: '30%' },
            ]
        },
        {
            section: 'Route Optimization', items: [
                { label: 'Batch Threshold', value: '5 parcels' },
                { label: 'Max Parcels per Route', value: '5' },
                { label: 'Max Detour (Return Pickup)', value: '2 km' },
                { label: 'Max Return Pickups', value: '3' },
            ]
        },
        {
            section: 'Payment', items: [
                { label: 'Modes Enabled', value: 'COD, Card (simulated), UPI (simulated)' },
                { label: 'Razorpay', value: 'Disabled — using COD + simulated' },
            ]
        },
        {
            section: 'Subscriptions', items: [
                { label: 'Starter', value: '₹99/mo — 5 free deliveries' },
                { label: 'Business', value: '₹499/mo — 25 free + 5% discount' },
                { label: 'Enterprise', value: '₹1,999/mo — Unlimited + 10% discount' },
            ]
        },
        {
            section: 'Integrations', items: [
                { label: 'n8n Webhook URL', value: 'Configured per environment' },
                { label: 'Google Maps APIs', value: 'Geocoding + Distance Matrix' },
                { label: 'OpenAI Model', value: 'GPT-4o-mini' },
                { label: 'Telegram Bot', value: 'aiogram 3.x' },
            ]
        },
    ];

    return (
        <div className="space-y-4 max-w-3xl">
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 text-sm text-yellow-700">
                ⚠️ Settings are read-only. Configuration changes must be made via environment variables and redeployment.
            </div>

            {config.map(section => (
                <div key={section.section} className="bg-white rounded-lg border border-gray-200">
                    <div className="px-4 py-3 border-b border-gray-100">
                        <h3 className="text-sm font-semibold text-gray-700">{section.section}</h3>
                    </div>
                    <div className="divide-y divide-gray-50">
                        {section.items.map(item => (
                            <div key={item.label} className="flex items-center justify-between px-4 py-2.5">
                                <span className="text-sm text-gray-600">{item.label}</span>
                                <span className="text-sm font-medium text-gray-800">{item.value}</span>
                            </div>
                        ))}
                    </div>
                </div>
            ))}
        </div>
    );
}
