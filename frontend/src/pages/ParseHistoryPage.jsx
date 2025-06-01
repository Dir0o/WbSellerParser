// src/pages/ParseHistoryPage.jsx
import { useState, useEffect } from "react";

export default function ParseHistoryPage({ token }) {
    const [rows, setRows] = useState([]);
    const [loading, setLoading] = useState(false);
    const [expanded, setExpanded] = useState(null);

    const API_BASE =
        import.meta.env.VITE_API_BASE ||
        `http://${window.location.hostname}:8000`;

    useEffect(() => {
        let mounted = true;

        async function fetchData() {
            setLoading(true);
            try {
                const res = await fetch(`${API_BASE}/parse-data`, {
                    headers: { Authorization: `Bearer ${token}` },
                });
                if (!res.ok) throw new Error(res.statusText);
                const json = await res.json();
                if (mounted) setRows(json.data ?? json);
            } catch {
                if (mounted) setRows([]);
            } finally {
                if (mounted) setLoading(false);
            }
        }

        fetchData();
        return () => { mounted = false; };
    }, [API_BASE, token]);

    const toggle = (id) => {
        setExpanded(expanded === id ? null : id);
    };

    return (
        <div className="min-h-screen w-screen bg-gray-100 flex flex-col items-center py-10 px-4 gap-8">
            <h1 className="text-2xl font-bold">История парсинга</h1>

            {loading && <p>Загрузка…</p>}

            {!loading && rows.length === 0 && (
                <p className="text-gray-600">Записи отсутствуют.</p>
            )}

            {rows.map((r) => (
                <div
                    key={r.id}
                    className="w-full max-w-2xl bg-white rounded-2xl shadow mb-4"
                >
                    <button
                        onClick={() => toggle(r.id)}
                        className="w-full text-left p-4 flex justify-between items-center"
                    >
                        <span>
                            #{r.id}&nbsp;—&nbsp;
                            {new Date(r.created_at).toLocaleString()}&nbsp;|&nbsp;
                            {(r.total_contacts ?? r.rows ?? 0)} записей
                        </span>
                        <span>{expanded === r.id ? "▲" : "▼"}</span>
                    </button>

                    {expanded === r.id && (
                        <div className="border-t p-4 text-sm overflow-x-auto">
                            <table className="w-full text-left table-auto">
                                <tbody>
                                    {Object.entries(r.params || r).map(
                                        ([k, v]) =>
                                            ["id", "created_at", "total_contacts", "rows"].includes(k) ? null : (
                                                <tr key={k}>
                                                    <td className="pr-4 font-semibold align-top">
                                                        {k}
                                                    </td>
                                                    <td>
                                                        {typeof v === "object"
                                                            ? JSON.stringify(v)
                                                            : String(v)}
                                                    </td>
                                                </tr>
                                            )
                                    )}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            ))}
        </div>
    );
}
