import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

const API_BASE = '/api';

async function fetchAPI(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const res = await fetch(url, {
        headers: { 'Content-Type': 'application/json', ...options.headers },
        ...options,
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `API error ${res.status}`);
    }
    return res.json();
}

// ── Dashboard ────────────────────────────────────────────

export function useStats() {
    return useQuery({
        queryKey: ['admin', 'stats'],
        queryFn: () => fetchAPI('/admin/stats'),
        refetchInterval: 30_000,
    });
}

export function useRevenueChart(days = 30) {
    return useQuery({
        queryKey: ['admin', 'revenue', days],
        queryFn: () => fetchAPI(`/admin/revenue-chart?days=${days}`),
        refetchInterval: 300_000,
    });
}

export function useFleetSummary() {
    return useQuery({
        queryKey: ['admin', 'fleet'],
        queryFn: () => fetchAPI('/admin/fleet-summary'),
        refetchInterval: 30_000,
    });
}

// ── Orders ───────────────────────────────────────────────

export function useOrders(params = {}) {
    const { status, skip = 0, limit = 50 } = params;
    const qs = new URLSearchParams();
    if (status) qs.set('status', status);
    qs.set('skip', skip);
    qs.set('limit', limit);

    return useQuery({
        queryKey: ['orders', status, skip, limit],
        queryFn: () => fetchAPI(`/orders/?${qs}`),
        refetchInterval: 30_000,
    });
}

export function useOrder(orderId) {
    return useQuery({
        queryKey: ['orders', orderId],
        queryFn: () => fetchAPI(`/orders/${orderId}`),
        enabled: !!orderId,
    });
}

export function useUpdateOrderStatus() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: ({ orderId, status }) =>
            fetchAPI(`/orders/${orderId}/status`, {
                method: 'PATCH',
                body: JSON.stringify({ status, actor_type: 'ADMIN' }),
            }),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ['orders'] });
            qc.invalidateQueries({ queryKey: ['admin', 'stats'] });
        },
    });
}

export function useGenerateOTP() {
    return useMutation({
        mutationFn: ({ orderId, otpType }) =>
            fetchAPI(`/orders/${orderId}/otp/generate?otp_type=${otpType}`, { method: 'POST' }),
    });
}

// ── Riders ───────────────────────────────────────────────

export function useRiders(status) {
    const qs = status ? `?status=${status}` : '';
    return useQuery({
        queryKey: ['riders', status],
        queryFn: () => fetchAPI(`/riders/${qs}`),
        refetchInterval: 30_000,
    });
}

export function useCreateRider() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (data) =>
            fetchAPI('/riders/', { method: 'POST', body: JSON.stringify(data) }),
        onSuccess: () => qc.invalidateQueries({ queryKey: ['riders'] }),
    });
}

export function useUpdateRiderStatus() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: ({ riderId, status }) =>
            fetchAPI(`/riders/${riderId}/status?status=${status}`, { method: 'PATCH' }),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ['riders'] });
            qc.invalidateQueries({ queryKey: ['admin', 'fleet'] });
        },
    });
}

// ── Warehouses ───────────────────────────────────────────

export function useWarehouses() {
    return useQuery({
        queryKey: ['warehouses'],
        queryFn: () => fetchAPI('/warehouses/'),
    });
}

// ── AI Insights ──────────────────────────────────────────

export function useInsights(params = {}) {
    const { limit = 20, category } = params;
    const qs = new URLSearchParams();
    qs.set('limit', limit);
    if (category) qs.set('category', category);

    return useQuery({
        queryKey: ['insights', category, limit],
        queryFn: () => fetchAPI(`/admin/insights?${qs}`),
    });
}

export function useGenerateInsights() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: () => fetchAPI('/admin/insights/generate', { method: 'POST' }),
        onSuccess: () => qc.invalidateQueries({ queryKey: ['insights'] }),
    });
}
