import { useState, useEffect, useMemo, useRef } from "react";
import codes from "../codes.json";


// Простая debounce-функция с методом cancel
function debounce(func, wait) {
    let timeout;
    function debounced(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func(...args), wait);
    }
    debounced.cancel = () => clearTimeout(timeout);
    return debounced;
}

export default function SearchPage({ token }) {
    const [query, setQuery] = useState("");
    const [suggestions, setSuggestions] = useState([]);
    const [showSuggestions, setShowSuggestions] = useState(false);
    const [details, setDetails] = useState([]);

    const [filterRegion, setFilterRegion] = useState("");
    const [salesFrom, setSalesFrom] = useState("");
    const [salesTo, setSalesTo] = useState("");
    const [dateFrom, setDateFrom] = useState("");
    const [dateTo, setDateTo] = useState("");
    const [category, setCategory] = useState("");
    const [createdFrom, setCreatedFrom] = useState("");
    const [createdTo, setCreatedTo] = useState("");

    const [showFilters, setShowFilters] = useState(false);
    const [loadingSuggest, setLoadingSuggest] = useState(false);
    const [loadingDetail, setLoadingDetail] = useState(false);
    const [loadingSale, setLoadingSale] = useState({});
    const [sortOption, setSortOption] = useState("fromA");
    const [showSort, setShowSort] = useState(false);

    const [firstLoad, setFirstLoad] = useState(true);

    const [catOptions, setCatOptions] = useState([]);

    const inputRef = useRef(null);
    const containerRef = useRef(null);
    const sortRef = useRef(null);
    const API_BASE =
        import.meta.env.VITE_API_BASE ||
        `http://${window.location.hostname}:8000`;

    useEffect(() => {
        (async () => {
            try {
                const res = await fetch(`${API_BASE}/search/distinct-categories`, {
                    headers: { Authorization: `Bearer ${token}` },
                });
                if (!res.ok) throw new Error();
                const json = await res.json();
                setCatOptions(json.data ?? json);
            } catch {
                setCatOptions([]);
            }
        })();
    }, [API_BASE, token]);

    // Отсортированный список регионов от 01 до 99
    const regionOptions = useMemo(
        () =>
            Object.entries(codes).sort(
                ([a], [b]) => parseInt(a, 10) - parseInt(b, 10)
            ),
        []
    );
    const sortedDetails = useMemo(() => {
        const arr = [...details];
        switch (sortOption) {
            case "fromA":
                return arr.sort((a, b) => a.store_name.localeCompare(b.store_name));
            case "fromZ":
                return arr.sort((a, b) => b.store_name.localeCompare(a.store_name));
            case "manySales":
                return arr.sort((a, b) => (b.saleCount || 0) - (a.saleCount || 0));
            case "fewSales":
                return arr.sort((a, b) => (a.saleCount || 0) - (b.saleCount || 0));
            case "newFirst":
                return arr.sort(
                    (a, b) => new Date(b.reg_date) - new Date(a.reg_date)
                );
            case "oldFirst":
                return arr.sort(
                    (a, b) => new Date(a.reg_date) - new Date(b.reg_date)
                );
            default:
                return arr;
        }
    }, [details, sortOption]);
    useEffect(() => {
        function handleClickOutside(e) {
            if (
                containerRef.current &&
                !containerRef.current.contains(e.target)
            ) {
                setShowSuggestions(false);
                setShowFilters(false);
            }
            if (
                sortRef.current &&
                !sortRef.current.contains(e.target)
            ) {
                setShowSort(false);
            }
        }
        document.addEventListener("mousedown", handleClickOutside);
        return () =>
            document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    const fetchSuggestions = useMemo(
        () =>
            debounce(async (q) => {
                if (!q.trim()) {
                    setSuggestions([]);
                    return;
                }
                setLoadingSuggest(true);
                try {
                    const params = new URLSearchParams();
                    params.append("q", q);
                    if (filterRegion) params.append("region", filterRegion);
                    if (salesFrom) params.append("salesFrom", salesFrom);
                    if (salesTo) params.append("salesTo", salesTo);
                    if (dateFrom) params.append("dateFrom", dateFrom);
                    if (dateTo) params.append("dateTo", dateTo);
                    if (category) params.append("category", category);              // +
                    if (createdFrom) params.append("createdFrom", createdFrom);      // +
                    if (createdTo) params.append("createdTo", createdTo);            // +

                    const res = await fetch(
                        `${API_BASE}/search?${params.toString()}&limit=10`,
                        { headers: { Authorization: `Bearer ${token}` } }
                    );
                    if (!res.ok) throw new Error(res.statusText);
                    const json = await res.json();
                    setSuggestions(json.data || []);
                    setShowSuggestions(true);
                } catch {
                    setSuggestions([]);
                } finally {
                    setLoadingSuggest(false);
                }
            }, 300),
        [
            API_BASE,
            token,
            filterRegion,
            salesFrom,
            salesTo,
            dateFrom,
            dateTo,
            category,
            createdFrom,
            createdTo,
        ]
    );

    useEffect(() => {
        fetchSuggestions(query);
        return () => fetchSuggestions.cancel();
    }, [query, fetchSuggestions]);

    function buildParams() {
        const p = new URLSearchParams();
        if (query.trim()) p.append("q", query);
        if (filterRegion) p.append("region", filterRegion);
        if (salesFrom) p.append("salesFrom", salesFrom);
        if (salesTo) p.append("salesTo", salesTo);
        if (dateFrom) p.append("dateFrom", dateFrom);
        if (dateTo) p.append("dateTo", dateTo);
        if (category) p.append("category", category);             // +
        if (createdFrom) p.append("createdFrom", createdFrom);    // +
        if (createdTo) p.append("createdTo", createdTo);          // +
        return p;
    }

    const handleSearch = async () => {
        inputRef.current?.blur();
        setShowSuggestions(false);
        setLoadingDetail(true);

        try {
            const res = await fetch(
                `${API_BASE}/search/results?${buildParams().toString()}`,
                { headers: { Authorization: `Bearer ${token}` } }
            );
            if (!res.ok) throw new Error(res.statusText);
            const json = await res.json();
            setDetails(json.data || []);
        } catch {
            setDetails([]);
        } finally {
            setLoadingDetail(false);
            setFirstLoad(false);
        }
    };

    const handleDownloadExcel = async () => {
        try {
            const res = await fetch(
                `${API_BASE}/search/xlsx?${buildParams().toString()}`,
                { headers: { Authorization: `Bearer ${token}` } }
            );
            if (!res.ok) throw new Error(res.statusText);
            const blob = await res.blob();
            const blobUrl = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = blobUrl;
            a.download = "search_results.xlsx";
            document.body.appendChild(a);
            a.click();
            a.remove();
        } catch {
            /* ignore */
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === "Enter") {
            e.preventDefault();
            handleSearch();
        }
    };

    function handleSetDateFrom(val) {
        if (dateTo && val > dateTo) setDateTo(val);
        setDateFrom(val);
    }
    function handleSetDateTo(val) {
        if (dateFrom && val < dateFrom) setDateFrom(val);
        setDateTo(val);
    }
    function handleSetCreatedFrom(val) {
        if (createdTo && val > createdTo) setCreatedTo(val);
        setCreatedFrom(val);
    }
    function handleSetCreatedTo(val) {
        if (createdFrom && val < createdFrom) setCreatedFrom(val);
        setCreatedTo(val);
    }

    /* ---------- выбор подсказки ---------- */
    const handleSelect = async (seller) => {
        setShowSuggestions(false);
        setSuggestions([]);
        setQuery(seller.store_name);
        await handleSearch();
    };

    async function updateSaleCount(sellerId) {
        setLoadingSale((prev) => ({ ...prev, [sellerId]: true }));
        try {
            const res = await fetch(
                `${API_BASE}/wb/update_seller_data?seller_id=${sellerId}`,
                { method: "POST", headers: { Authorization: `Bearer ${token}` } }
            );
            if (!res.ok) throw new Error(res.statusText);
            const json = await res.json();
            const newCount = json.saleItemQuantity ?? json.data?.saleItemQuantity;
            if (newCount != null) {
                setDetails((prev) =>
                    prev.map((d) =>
                        d.seller_id === sellerId ? { ...d, saleCount: newCount } : d
                    )
                );
            }
        } catch {
            /* ignore */
        } finally {
            setLoadingSale((prev) => ({ ...prev, [sellerId]: false }));
        }
    }

    return (
        <div className="min-h-screen w-screen bg-gray-100 flex flex-col items-center py-10 px-4 gap-8">
            <h1 className="text-2xl font-bold">Поиск продавца</h1>
            <div ref={containerRef} className="relative w-full max-w-2xl">
                {/* Обёртка для input + иконки */}
                <div className="flex gap-2">
                    <div className="relative flex-1 border rounded">
                        <input
                            ref={inputRef}
                            type="text"
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            onKeyDown={handleKeyDown}
                            onFocus={() => query.trim() && setShowSuggestions(true)}
                            placeholder="Начните вводить название..."
                            className="w-full p-3 pr-10 border-none rounded focus:outline-none"
                        />
                        <button
                            onClick={handleSearch}
                            className="absolute top-2.5 right-2 bg-transparent flex items-center px-1 py-1
                             hover:bg-gray-200 border-none transition focus:outline-none "
                        >
                            <svg
                                xmlns="http://www.w3.org/2000/svg"
                                className="h-5 w-5"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                            >
                                <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={2}
                                    d="M21 21l-6-6m2-5a7 7 0 10-14 0 7 7 0 0014 0z"
                                />
                            </svg>
                        </button>
                    </div>
                    <button
                        onClick={() => setShowFilters((f) => !f)}
                        className="px-4 bg-gray-200 rounded focus:outline-none"
                    >
                        Фильтр
                    </button>
                </div>

                {showFilters && (
                    <div className="mt-2 p-4 bg-white border rounded shadow">
                        {/* регион */}
                        <div className="mb-2">
                            <label className="block mb-1">Регион</label>
                            <select
                                value={filterRegion}
                                onChange={(e) => setFilterRegion(e.target.value)}
                                className="w-full p-1 border rounded"
                            >
                                <option value="">Не важно</option>
                                {regionOptions.map(([code, name]) => (
                                    <option key={code} value={code}>
                                        {code} | {name}
                                    </option>
                                ))}
                            </select>
                        </div>

                        {/* продажи */}
                        <div className="mb-2 flex gap-2">
                            <div className="flex-1">
                                <label className="block mb-1">Продажи от</label>
                                <input
                                    type="number"
                                    value={salesFrom}
                                    onChange={(e) => setSalesFrom(e.target.value)}
                                    className="w-full p-1 border rounded"
                                />
                            </div>
                            <div className="flex-1">
                                <label className="block mb-1">Продажи до</label>
                                <input
                                    type="number"
                                    value={salesTo}
                                    onChange={(e) => setSalesTo(e.target.value)}
                                    className="w-full p-1 border rounded"
                                />
                            </div>
                        </div>

                        {/* дата регистрации продавца */}
                        <div className="mb-2 flex gap-2">
                            <div className="flex-1">
                                <label className="block mb-1">Дата рег. от</label>
                                <input
                                    type="date"
                                    value={dateFrom}
                                    max={dateTo || undefined}
                                    onChange={(e) => handleSetDateFrom(e.target.value)}
                                    className="w-full p-1 border rounded"
                                />
                            </div>
                            <div className="flex-1">
                                <label className="block mb-1">Дата рег. до</label>
                                <input
                                    type="date"
                                    value={dateTo}
                                    min={dateFrom || undefined}
                                    onChange={(e) => handleSetDateTo(e.target.value)}
                                    className="w-full p-1 border rounded"
                                />
                            </div>
                        </div>

                        {/* ▼▼▼ НОВОЕ ▼▼▼ */}
                        {/* категория */}
                        <div className="mb-2">
                            <label className="block mb-1">Категория</label>
                            <select
                                value={category}
                                onChange={(e) => setCategory(e.target.value)}
                                className="w-full p-1 border rounded"
                            >
                                <option value="">Не важно</option>
                                {catOptions.map((c) => (
                                    <option key={c} value={c}>
                                        {c}
                                    </option>
                                ))}
                            </select>
                        </div>

                        {/* дата выгрузки */}
                        <div className="mb-2 flex gap-2">
                            <div className="flex-1">
                                <label className="block mb-1">Дата выгрузки от</label>
                                <input
                                    type="date"
                                    value={createdFrom}
                                    max={createdTo || undefined}
                                    onChange={(e) =>
                                        handleSetCreatedFrom(e.target.value)
                                    }
                                    className="w-full p-1 border rounded"
                                />
                            </div>
                            <div className="flex-1">
                                <label className="block mb-1">Дата выгрузки до</label>
                                <input
                                    type="date"
                                    value={createdTo}
                                    min={createdFrom || undefined}
                                    onChange={(e) =>
                                        handleSetCreatedTo(e.target.value)
                                    }
                                    className="w-full p-1 border rounded"
                                />
                            </div>
                        </div>
                        {/* ▲▲▲ НОВОЕ ▲▲▲ */}
                    </div>
                )}

                {loadingSuggest && (
                    <div className="absolute top-2 right-2 animate-spin">⏳</div>
                )}
                {showSuggestions && suggestions.length > 0 && (
                    <ul className="absolute w-full bg-white border mt-1 max-h-48 overflow-y-auto z-10">
                        {suggestions.map((s) => (
                            <li
                                key={s.id}
                                className="p-2 hover:bg-gray-100 cursor-pointer"
                                onMouseDown={() => handleSelect(s)}
                            >
                                {s.store_name}
                            </li>
                        ))}
                    </ul>
                )}
            </div>

            {loadingDetail && firstLoad == true &&
                <p className="w-full text-center max-w-md bg-white rounded-2xl shadow p-6 mt-6 overflow-y-auto">
                    Загрузка данных…
                </p>}

            {details.length > 0 && (
                loadingDetail == false && <div
                    className="w-full max-w-md bg-white rounded-2xl shadow p-6 mt-6 overflow-y-auto"
                    style={{ maxHeight: "70vh" }}
                >
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-xl font-semibold">Найдено: {details.length}</h2>
                        <button
                            onClick={handleDownloadExcel}
                            className="bg-green-600 hover:bg-green-700 text-white py-1 px-3 rounded transition"
                        >
                            Скачать Excel
                        </button>
                    </div>
                    <div className="relative mb-4" ref={sortRef}>
                        <button
                            onClick={() => setShowSort((s) => !s)}
                            className="bg-white hover:bg-gray-100 text-gray-800 py-1 px-2 border rounded focus:outline-none"
                        >
                            Сортировать:
                        </button>
                        {showSort && (
                            <div className="absolute mt-2 bg-white border rounded shadow w-48 z-10">
                                <label className="flex items-center px-3 py-1 hover:bg-gray-50">
                                    <input
                                        type="radio"
                                        name="sort"
                                        className="mr-2"
                                        checked={sortOption === "fromA"}
                                        onChange={() => setSortOption("fromA")}
                                    />
                                    От А
                                </label>
                                <label className="flex items-center px-3 py-1 hover:bg-gray-50">
                                    <input
                                        type="radio"
                                        name="sort"
                                        className="mr-2"
                                        checked={sortOption === "fromZ"}
                                        onChange={() => setSortOption("fromZ")}
                                    />
                                    От Я
                                </label>
                                <label className="flex items-center px-3 py-1 hover:bg-gray-50">
                                    <input
                                        type="radio"
                                        name="sort"
                                        className="mr-2"
                                        checked={sortOption === "manySales"}
                                        onChange={() => setSortOption("manySales")}
                                    />
                                    Сначала много продаж
                                </label>
                                <label className="flex items-center px-3 py-1 hover:bg-gray-50">
                                    <input
                                        type="radio"
                                        name="sort"
                                        className="mr-2"
                                        checked={sortOption === "fewSales"}
                                        onChange={() => setSortOption("fewSales")}
                                    />
                                    Сначала мало продаж
                                </label>
                                <label className="flex items-center px-3 py-1 hover:bg-gray-50">
                                    <input
                                        type="radio"
                                        name="sort"
                                        className="mr-2"
                                        checked={sortOption === "newFirst"}
                                        onChange={() => setSortOption("newFirst")}
                                    />
                                    Дата, сперва новые
                                </label>
                                <label className="flex items-center px-3 py-1 hover:bg-gray-50">
                                    <input
                                        type="radio"
                                        name="sort"
                                        className="mr-2"
                                        checked={sortOption === "oldFirst"}
                                        onChange={() => setSortOption("oldFirst")}
                                    />
                                    Дата, сперва старые
                                </label>
                            </div>
                        )}
                    </div>
                    <ul className="overflow-y-auto divide-y pr-2 text-sm break-words">
                        {sortedDetails.map((detail) => (
                            <li key={detail.id} className="py-2">
                                <div>
                                    <strong>Название:</strong> {detail.store_name}
                                </div>
                                <div>
                                    <strong>ID:</strong> {detail.seller_id}
                                </div>
                                <div>
                                    <strong>Ссылка:</strong>{" "}
                                    <a href={detail.url} target="_blank" rel="noopener noreferrer">
                                        {detail.url}
                                    </a>
                                </div>
                                {detail.ogrn && (
                                    <div>
                                        <strong>ОГРН:</strong> {detail.ogrn}
                                    </div>
                                )}
                                {detail.ogrnip && (
                                    <div>
                                        <strong>ОГРНИП:</strong> {detail.ogrnip}
                                    </div>
                                )}
                                <div>
                                    <strong>Налоговый орган:</strong> {detail.tax_office}
                                </div>
                                {detail.saleCount != null && (
                                    <div className="flex items-center gap-2">
                                        <strong>Продаж:</strong>{" "}
                                        {detail.saleCount}
                                        <button
                                            onClick={() =>
                                                updateSaleCount(detail.seller_id)
                                            }
                                            className="p-0 text-gray-500 border-none hover:text-gray-800 hover:border-none hover:fill-gray-500 focus:outline-none"
                                        >
                                            {loadingSale[detail.seller_id] ? (
                                                /* маленький спиннер */
                                                <svg
                                                    className="h-4 w-4 animate-spin"
                                                    xmlns="http://www.w3.org/2000/svg"
                                                    fill="none"
                                                    viewBox="0 0 24 24"
                                                    stroke="currentColor"
                                                >
                                                    <g><rect x="11" y="1" width="2" height="5" opacity=".14"/><rect x="11" y="1" width="2" height="5" transform="rotate(30 12 12)" opacity=".29"/><rect x="11" y="1" width="2" height="5" transform="rotate(60 12 12)" opacity=".43"/><rect x="11" y="1" width="2" height="5" transform="rotate(90 12 12)" opacity=".57"/><rect x="11" y="1" width="2" height="5" transform="rotate(120 12 12)" opacity=".71"/><rect x="11" y="1" width="2" height="5" transform="rotate(150 12 12)" opacity=".86"/><rect x="11" y="1" width="2" height="5" transform="rotate(180 12 12)"/><animateTransform attributeName="transform" type="rotate" calcMode="discrete" dur="0.75s" values="0 12 12;30 12 12;60 12 12;90 12 12;120 12 12;150 12 12;180 12 12;210 12 12;240 12 12;270 12 12;300 12 12;330 12 12;360 12 12" repeatCount="indefinite"/></g>
                                                </svg>
                                            ) : (
                                                /* ——— новая иконка ——— */
                                                <svg
                                                    xmlns="http://www.w3.org/2000/svg"
                                                    viewBox="0 0 490.563 490.563"
                                                    className="h-3 w-3"
                                                >
                                                    <path d="M331.004,128.766c-2.1,11.4,5.2,21.8,16.6,23.9l102,17.7c12.1,1.9,20.1-6.6,22.9-17.7l17.7-102 c2.1-11.4-5.2-21.8-16.6-23.9s-21.8,5.2-23.9,16.6l-9,54.7c-45.7-60.7-117.9-97.8-195.8-97.9c-146.7,0-243.9,116.3-244.9,244.9 c-0.5,65.4,49.8,232.9,244.8,244.8c195.2,11.9,244.8-179.4,244.8-244.8c0-11.3-9.2-20.5-20.5-20.5s-20.5,9.2-20.5,20.5 c0,112.4-91.4,203.8-203.8,203.8s-203.8-91.4-203.8-203.8s91.4-203.8,203.8-203.8c63.9,0,123.3,30.1,161.4,79.3l-51.2-8.5 C343.504,109.966,333.104,117.266,331.004,128.766z" />
                                                </svg>
                                            )}
                                        </button>
                                    </div>
                                )}
                                {detail.reg_date && (
                                    <div>
                                        <strong>Дата рег.:</strong>{" "}
                                        {new Date(detail.reg_date).toLocaleDateString()}
                                    </div>
                                )}

                                <div>
                                    <strong>Телефон:</strong> {" "}
                                    {Array.isArray(detail.phone) ? detail.phone.join(", ") : detail.phone || "Не найдено"}
                                </div>
                                <div>
                                    <strong>Почта:</strong> {" "}
                                    {Array.isArray(detail.email) ? detail.email.join(", ") : detail.email || "Не найдено"}
                                </div>
                            </li>
                        ))}
                    </ul>
                </div>
                || loadingDetail == true && <p className="w-full text-center max-w-md bg-white rounded-2xl shadow p-6 mt-6 overflow-y-auto">Загрузка данных…</p> )
                || loadingDetail == false && firstLoad == false &&
                <p className="w-full text-center max-w-md bg-white rounded-2xl shadow p-6 mt-6 overflow-y-auto">
                    По вашему запросу ничего не найдено!
                </p>}
        </div>
    );
}
