import { useState, useEffect, Fragment } from "react";
import Cookies from "js-cookie"
import { Dialog, Transition } from "@headlessui/react";
import Select, { components } from "react-select";

function GearIndicator(props) {
    const {
        selectProps: { openModal },
        innerProps,
    } = props;

    return (
        <components.DropdownIndicator {...props}>
            <span
                {...innerProps}
                onMouseDown={e => {
                    e.preventDefault();      // блокируем стандартный фокус
                    openModal();
                }}
                className="cursor-pointer text-lg leading-none"
            >
                ⚙
            </span>
        </components.DropdownIndicator>
    );
}

//
export default function ParserWB({ token, onLogout, categories, codes }) {
    const [lvl1, setLvl1] = useState("");
    const [lvl2, setLvl2] = useState("");
    const [lvl3, setLvl3] = useState("");
    const [minSales, setMinSales] = useState(0);
    const [maxSales, setMaxSales] = useState("");
    const [regDate, setRegDate] = useState("");
    const [maxRegDate, setMaxRegDate] = useState("");
    /* ---------- регионы ---------- */
    const [regions, setRegions] = useState([]);   // ['77','50',…]
    const regionStr = regions.join(",");
    const [isOpen, setIsOpen] = useState(false);
    const [tempSel, setTempSel] = useState([]);

    /* ---------- опции для модала ---------- */
    const regionOptions = Object.entries(codes)
        .sort(([a], [b]) => {
            const aZero = a.startsWith("0");
            const bZero = b.startsWith("0");
            if (aZero !== bZero) return aZero ? -1 : 1;
            return a.localeCompare(b);
        })
        .map(([code, name]) => ({ value: code, label: `${code} ${name}` }));


    const [region, setRegion] = useState("");
    const [pages, setPages] = useState(1);
    const [limit, setLimit] = useState(0);            // лимит только для парсинга
    const [lastCollected, setLastCollected] = useState(null);   // <─ Новое
    const [loading, setLoading] = useState(false);
    const [items, setItems] = useState(null);
    const [error, setError] = useState("");

    const API_BASE =
        import.meta.env.VITE_API_BASE ||
        `http://${window.location.hostname}:8000`;

    const sortedRegions = Object.entries(codes).sort(([a], [b]) => {
        const aZero = a.startsWith("0");
        const bZero = b.startsWith("0");
        if (aZero !== bZero) return aZero ? -1 : 1;
        return a.localeCompare(b);
    });

    const c1 = categories[lvl1];
    const c2 = c1?.childs?.[lvl2];
    const c3 = c2?.childs?.[lvl3];

    /* ───────── Дата последнего сбора ───────── */
    useEffect(() => {
        const deepest = c2?.childs?.[lvl3] || c2 || c1;
        if (!deepest || !region) {
            setLastCollected(null);
            return;
        }
        const { shard, query } = deepest;

        let url =
            `${API_BASE}/wb/cat/last?${query}` +
            `&shard=${shard}` +
            `&region_id=${regionStr}` +
            `&saleItemCount=${minSales}` +
            `&pages=${pages}`;
        if (maxSales) url += `&maxSaleCount=${maxSales}`;

        (async () => {
            try {
                const res = await fetch(url, {
                    headers: { Authorization: `Bearer ${token}` },
                });
                if (!res.ok) {
                    setLastCollected(null);
                    return;
                }
                const j = await res.json();
                setLastCollected(j?.data?.last_collected ?? null);
            } catch {
                setLastCollected(null);
            }
        })();
        // ограничиваем список зависимостей — даты регистрации и limit
        // здесь не участвуют, как и требуется
    }, [lvl1, lvl2, lvl3, minSales, maxSales, region, pages]);

    /* ───────── handleSubmit (без изменений в верстке) ───────── */
    async function handleSubmit(e) {
        e.preventDefault();
        setError("");
        setLoading(true);
        try {
            const deepest = c2?.childs?.[lvl3] || c2 || c1;
            const { shard, query } = deepest;
            let url =
                `${API_BASE}/wb/cat?${query}` +
                `&shard=${shard}` +
                `&region_id=${regionStr}` +
                `&saleItemCount=${minSales}` +
                `&pages=${pages}` +
                `&limit=${limit}`;
            if (maxSales) url += `&maxSaleCount=${maxSales}`;
            if (regDate) url += `&regDate=${regDate}`;
            if (maxRegDate) url += `&maxRegDate=${maxRegDate}`;

            const res = await fetch(url, {
                headers: { Authorization: `Bearer ${token}` },
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const json = await res.json();
            setItems(json.data);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }

    async function downloadExcel() {
        setError("");
        setLoading(true);

        try {
            const deepest = c2?.childs?.[lvl3] || c2 || c1;
            const { shard, query } = deepest;

            let url =
                `${API_BASE}/wb/cat/xlsx?${query}` +
                `&shard=${shard}` +
                `&region_id=${regionStr}` +
                `&saleItemCount=${minSales}` +
                `&pages=${pages}` +
                `&limit=${limit}` +
                `&format=excel`;
            if (maxSales)   url += `&maxSaleCount=${maxSales}`;
            if (regDate)    url += `&regDate=${regDate}`;
            if (maxRegDate) url += `&maxRegDate=${maxRegDate}`;

            const res = await fetch(url, {
                method: "GET",
                headers: { Authorization: `Bearer ${token}` },
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);

            const blob = await res.blob();
            const blobUrl = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = blobUrl;
            a.download = "report.xlsx";
            document.body.appendChild(a);
            a.click();
            a.remove();
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="min-h-screen w-screen bg-gray-100 flex flex-col items-center py-10 px-4 gap-8 relative">

            {loading && (
                <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50">
                    <div className="h-20 w-20 border-8 border-violet-400 border-t-transparent rounded-full animate-spin" />
                </div>
            )}

            <form
                onSubmit={handleSubmit}
                className="w-full max-w-xl bg-white rounded-2xl shadow p-6 space-y-4"
            >
                <h1 className="text-2xl font-semibold text-center">Парсер Wildberries</h1>
                {lastCollected && (
                    <div className="text-xs text-gray-600 text-center">
                        Последний сбор с текущими параметрами:&nbsp;
                        <u>{new Date(lastCollected).toLocaleString()}</u>
                    </div>
                )}
                {/* Категории */}
                <div>
                    <label className="block mb-1 font-medium">Категория</label>
                    <select
                        className="w-full p-2 border rounded"
                        value={lvl1}
                        onChange={e => { setLvl1(e.target.value); setLvl2(""); setLvl3(""); }}
                        required
                    >
                        <option value="" disabled>Выберите категорию</option>
                        {categories.map((c, i) => (
                            <option key={i} value={i}>{c.name}</option>
                        ))}
                    </select>
                </div>

                {c1?.childs && (
                    <div>
                        <label className="block mb-1 font-medium">Подкатегория</label>
                        <select
                            className="w-full p-2 border rounded"
                            value={lvl2}
                            onChange={e => { setLvl2(e.target.value); setLvl3(""); }}
                            required
                        >
                            <option value="" disabled>Выберите подкатегорию</option>
                            {c1.childs.map((c, i) => (
                                <option key={i} value={i}>{c.name}</option>
                            ))}
                        </select>
                    </div>
                )}

                {c2?.childs && (
                    <div>
                        <label className="block mb-1 font-medium">Третья категория</label>
                        <select
                            className="w-full p-2 border rounded"
                            value={lvl3}
                            onChange={e => setLvl3(e.target.value)}
                            required
                        >
                            <option value="" disabled>Выберите категорию</option>
                            {c2.childs.map((c, i) => (
                                <option key={i} value={i}>{c.name}</option>
                            ))}
                        </select>
                    </div>
                )}

                {/* Мин. / Макс. продаж и Лимит */}
                <div>
                    <label className="block mb-1 font-medium">Мин. продаж</label>
                    <input
                        type="number"
                        min="0"
                        value={minSales}
                        onChange={e => setMinSales(Number(e.target.value))}
                        className="w-full p-2 border rounded"
                        required
                    />
                </div>
                <div>
                    <label className="block mb-1 font-medium">Макс. продаж</label>
                    <input
                        type="number"
                        min="0"
                        value={maxSales}
                        onChange={e => setMaxSales(e.target.value)}
                        className="w-full p-2 border rounded"
                    />
                </div>
                <div>
                    <label className="block mb-1 font-medium">Лимит (0 - без лимита)</label>
                    <input
                        type="number"
                        min="0"
                        max="1000"
                        value={limit}
                        onChange={e => setLimit(Math.max(0, Number(e.target.value)))}
                        className="w-full p-2 border rounded"
                        required
                    />
                </div>

                {/* Мин. / Макс. дата регистрации */}
                <div>
                    <label className="block mb-1 font-medium">Мин. дата регистрации магазина</label>
                    <input
                        type="date"
                        value={regDate}
                        onChange={e => setRegDate(e.target.value)}
                        className="w-full p-2 border rounded"
                        required
                    />
                </div>
                <div>
                    <label className="block mb-1 font-medium">Макс. дата регистрации магазина</label>
                    <input
                        type="date"
                        value={maxRegDate}
                        onChange={e => setMaxRegDate(e.target.value)}
                        className="w-full p-2 border rounded"
                        required
                    />
                </div>

                {/* Регион */}
                <div>
                    <label className="block mb-1 font-medium">Регионы</label>
                    <Select
                        isMulti
                        value={regionOptions.filter(o => regions.includes(o.value))}
                        onChange={opts => setRegions(opts.map(o => o.value))}
                        menuIsOpen={false}               /* меню выключено */
                        closeMenuOnSelect={false}
                        isSearchable={false}
                        placeholder="Нажмите ⚙ чтобы выбрать"
                        components={{
                            DropdownIndicator: GearIndicator,
                            IndicatorSeparator: () => null,
                        }}
                        openModal={() => { setTempSel(regions); setIsOpen(true); }}  /* передаём в индикатор */
                        classNamePrefix="select"
                        className="w-full"
                    />
                </div>

                {/* --- модал --- */}
                <Transition appear show={isOpen} as={Fragment}>
                    <Dialog as="div" className="relative z-10" onClose={setIsOpen}>
                        <Transition.Child
                            as={Fragment}
                            enter="ease-out duration-300"
                            enterFrom="opacity-0"
                            enterTo="opacity-100"
                            leave="ease-in duration-200"
                            leaveFrom="opacity-100"
                            leaveTo="opacity-0"
                        >
                            <div className="fixed inset-0 bg-black/30" />
                        </Transition.Child>

                        <div className="fixed inset-0 overflow-y-auto">
                            <div className="flex min-h-full items-center justify-center p-4 text-center">
                                <Transition.Child
                                    as={Fragment}
                                    enter="ease-out duration-300"
                                    enterFrom="opacity-0 scale-95"
                                    enterTo="opacity-100 scale-100"
                                    leave="ease-in duration-200"
                                    leaveFrom="opacity-100 scale-100"
                                    leaveTo="opacity-0 scale-95"
                                >
                                    <Dialog.Panel className="w-full max-w-md transform overflow-hidden rounded-2xl bg-white p-6 text-left align-middle shadow-xl transition-all">
                                        <Dialog.Title className="text-lg font-medium mb-4">
                                            Массовый выбор регионов
                                        </Dialog.Title>

                                        <div className="max-h-60 overflow-y-auto space-y-2 mb-4 pr-2">
                                            {regionOptions.map(({ value, label }) => (
                                                <label
                                                    key={value}
                                                    className="flex items-center gap-2 select-none"
                                                >
                                                    <input
                                                        type="checkbox"
                                                        checked={tempSel.includes(value)}
                                                        onChange={e => {
                                                            if (e.target.checked) {
                                                                setTempSel([...tempSel, value]);
                                                            } else {
                                                                setTempSel(tempSel.filter(r => r !== value));
                                                            }
                                                        }}
                                                    />
                                                    <span>{label}</span>
                                                </label>
                                            ))}
                                        </div>

                                        <div className="mt-2 flex gap-2 justify-end">
                                            <button
                                                type="button"
                                                className="px-4 py-2 rounded bg-gray-200"
                                                onClick={() => setIsOpen(false)}
                                            >
                                                Отмена
                                            </button>
                                            <button
                                                type="button"
                                                className="px-4 py-2 rounded bg-violet-600 text-white"
                                                onClick={() => {
                                                    setRegions(tempSel);
                                                    setIsOpen(false);
                                                }}
                                            >
                                                Готово
                                            </button>
                                        </div>
                                    </Dialog.Panel>
                                </Transition.Child>
                            </div>
                        </div>
                    </Dialog>
                </Transition>

                {/* Страницы */}
                <div>
                    <label className="block mb-1 font-medium">Количество страниц (до 50)</label>
                    <input
                        type="number"
                        min="1"
                        max="50"
                        value={pages}
                        onChange={e => setPages(Number(e.target.value))}
                        className="w-full p-2 border rounded"
                        required
                    />
                </div>

                <div className="flex gap-4">
                    <button
                        type="submit"
                        disabled={loading}
                        className="flex-1 bg-violet-600 hover:bg-violet-700 text-white py-2 rounded transition"
                    >
                        {loading ? "Загрузка…" : "Показать"}
                    </button>
                    <button
                        type="button"
                        onClick={downloadExcel}
                        disabled={loading}
                        className="flex-1 bg-green-600 hover:bg-green-700 text-white py-2 rounded transition"
                    >
                        {loading ? "Генерация..." : "Скачать Excel"}
                    </button>
                </div>
            </form>

            {error && <div className="text-red-500">{error}</div>}

            {items && (
                <div className="w-full max-w-xl bg-white rounded-2xl shadow p-6 mt-6 overflow-y-auto" style={{ maxHeight: "70vh" }}>
                    <h2 className="text-xl font-semibold mb-4">Найдено: {items.length}</h2>
                    <ul className="overflow-y-auto divide-y pr-2 text-sm break-words">
                        {items.map((it, idx) => (
                            <li key={idx} className="py-2">
                                <div><strong>Магазин:</strong> {it.store_name}</div>
                                <div><strong>ИНН:</strong> {it.inn}</div>
                                {it.ogrn && <div><strong>ОГРН:</strong> {it.ogrn}</div>}
                                {it.ogrnip && <div><strong>ОГРНИП:</strong> {it.ogrnip}</div>}
                                <div><strong>Налоговый орган:</strong> {it.tax_office}</div>
                                <div>
                                    <strong>URL:</strong> <a href={it.url} target="_blank" rel="noopener noreferrer">{it.url}</a>
                                </div>
                                <div><strong>Дата рег.:</strong> {new Date(it.reg_date).toLocaleString()}</div>
                                <div><strong>Продаж:</strong> {it.saleCount}</div>
                                <div>
                                    <strong>Телефон:</strong> {" "}
                                    {Array.isArray(it.phone)
                                        ? (it.phone.length ? it.phone.join(", ") : "Не найдено")
                                        : (it.phone || "Не найдено")}
                                </div>
                                <div>
                                    <strong>Почта:</strong> {" "}
                                    {Array.isArray(it.email)
                                        ? (it.email.length ? it.email.join(", ") : "Не найдено")
                                        : (it.email || "Не найдено")}
                                </div>
                            </li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    );
}