import { useWarehouses } from '../api/client';
import Spinner from '../components/ui/Spinner';

export default function Warehouses() {
    const { data: warehouses, isLoading } = useWarehouses();

    if (isLoading) return <Spinner />;

    if (!warehouses || warehouses.length === 0) {
        return <div className="text-center text-gray-400 py-12">No warehouses configured</div>;
    }

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {warehouses.map(wh => {
                const utilization = wh.capacity > 0 ? Math.round((wh.current_load / wh.capacity) * 100) : 0;
                const barColor = utilization > 85 ? 'bg-red-500' : utilization > 60 ? 'bg-yellow-500' : 'bg-green-500';

                return (
                    <div key={wh.id} className="bg-white rounded-lg border border-gray-200 p-5">
                        <div className="flex items-center justify-between mb-3">
                            <h3 className="font-semibold text-gray-800">{wh.name}</h3>
                            <span className={`w-2.5 h-2.5 rounded-full ${wh.is_active ? 'bg-green-500' : 'bg-gray-300'}`} />
                        </div>
                        <p className="text-sm text-gray-500 mb-4">{wh.address}</p>

                        <div className="space-y-2">
                            <div className="flex justify-between text-sm">
                                <span className="text-gray-500">Capacity</span>
                                <span className="font-medium">{wh.current_load} / {wh.capacity}</span>
                            </div>
                            <div className="w-full bg-gray-100 rounded-full h-2">
                                <div className={`h-2 rounded-full ${barColor}`} style={{ width: `${Math.min(utilization, 100)}%` }} />
                            </div>
                            <div className="text-right text-xs text-gray-400">{utilization}% utilized</div>
                        </div>

                        <div className="mt-3 pt-3 border-t border-gray-100 grid grid-cols-2 gap-2 text-xs text-gray-500">
                            <div>Lat: {wh.lat}</div>
                            <div>Lng: {wh.lng}</div>
                            {wh.city && <div className="col-span-2">City: {wh.city}</div>}
                        </div>
                    </div>
                );
            })}
        </div>
    );
}
