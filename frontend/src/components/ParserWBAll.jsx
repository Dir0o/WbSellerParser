import { useState, useEffect, Fragment } from "react";
import Cookies from "js-cookie";

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

export default function ParserWBAll({ token, onLogout, categories, codes }) {
    const [lvl1, setLvl1] = useState("");
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
    const [limit, setLimit] = useState(0);            // новый параметр
    const [lastCollected, setLastCollected] = useState(null);  // ← памятка
    const [loading, setLoading] = useState(false);
    const [items, setItems] = useState([]);
    const [error, setError] = useState("");
    const [jobId, setJobId] = useState(null);

    const API_BASE =
        import.meta.env.VITE_API_BASE ||
        `http://${window.location.hostname}:8000`;

    const sortedRegions = Object.entries(codes).sort(([a], [b]) => {
        const aZero = a.startsWith("0");
        const bZero = b.startsWith("0");
        if (aZero !== bZero) return aZero ? -1 : 1;
        return a.localeCompare(b);
    });

    const mainCategory = categories[lvl1];


    useEffect(() => {
        if (!mainCategory || !region) {      // нужны обязательные поля
            setLastCollected(null);
            return;
        }

        let url =
            `${API_BASE}/wb/all/last?main_id=${mainCategory.id}` +
            `&region_id=${regionStr}` +
            `&saleItemCount=${minSales}` +
            `&pages=${pages}`;
        if (maxSales) url += `&maxSaleCount=${maxSales}`;
        // limit / regDate / maxRegDate *не* добавляем — они не участвуют в хэше

        (async () => {
            try {
                const res = await fetch(url, {
                    headers: { Authorization: `Bearer ${token}` },
                });
                if (!res.ok) { setLastCollected(null); return; }
                const j = await res.json();
                setLastCollected(j?.data?.last_collected ?? null);
            } catch {
                setLastCollected(null);
            }
        })();
    // следим только за «значимыми» параметрами
    }, [lvl1, minSales, maxSales, region, pages]);

    async function handleSubmit(e) {
        e.preventDefault();
        setError("");
        setLoading(true);
        setItems([]);

        try {
            const main_id = mainCategory.id;
            // 1) Запускаем фоновую задачу
            let startUrl = `${API_BASE}/parse?main_id=${main_id}`;
            startUrl += `&region_id=${regionStr}`;
            startUrl += `&saleItemCount=${minSales}`;
            startUrl += `&pages=${pages}`;
            if (maxSales)    startUrl += `&maxSaleCount=${maxSales}`;
            if (regDate)     startUrl += `&regDate=${regDate}`;
            if (maxRegDate)  startUrl += `&maxRegDate=${maxRegDate}`;
            if (limit)       startUrl += `&limit=${limit}`;

            const startRes = await fetch(startUrl, {
                method: "POST",
                headers: { Authorization: `Bearer ${token}` },
            });
            if (!startRes.ok) throw new Error(`HTTP ${startRes.status}`);
            const { job_id: newJobId } = await startRes.json();
            // сохраняем jobId в стейт, чтобы кнопка Excel знала, какую задачу качать
            setJobId(newJobId);
            // 2) Ждём, пока статус не станет finished
            let status;
            while (true) {
                await new Promise(r => setTimeout(r, 1000));
                // используем локальную переменную newJobId, иначе jobId в стейте может быть ещё null
                const stRes = await fetch(`${API_BASE}/parse/jobs/${newJobId}/status`, {
                    headers: { Authorization: `Bearer ${token}` },
                });
                if (!stRes.ok) throw new Error(`Status HTTP ${stRes.status}`);
                const { status: s } = await stRes.json();
                if (s === "finished") break;
                if (s === "failed") throw new Error("Парсинг не удался");
            }

            // 3) Забираем результат
            const resRes = await fetch(`${API_BASE}/parse/jobs/${newJobId}/result`, {
                headers: { Authorization: `Bearer ${token}` },
            });
            if (!resRes.ok) throw new Error(`HTTP ${resRes.status}`);
            const data = await resRes.json();
            setItems(data);

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
            if (!jobId) throw new Error("Сначала запустите парсинг, чтобы получить job_id");
            const res = await fetch(`${API_BASE}/parse/jobs/${jobId}/excel`, {
                headers: { Authorization: `Bearer ${token}` },
            });
            if (res.status === 202) {
                setError("Excel ещё формируется, попробуйте позже.");
                return;
            }
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const blob = await res.blob();
            const blobUrl = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = blobUrl;
            a.download = `report_${jobId}.xlsx`;
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
                <h1 className="text-2xl font-semibold text-center">
                    Парсер Wildberries All
                </h1>
                {lastCollected && (
                    <div className="text-xs text-gray-600 text-center">
                        Последний сбор с текущими параметрами:&nbsp;
                        <u>{new Date(lastCollected).toLocaleString()}</u>
                    </div>
                )}
                {/* Категория */}
                <div>
                    <label className="text-center block mb-1 font-medium">Категория</label>
                    <select
                        className="w-full p-2 border rounded"
                        value={lvl1}
                        onChange={(e) => setLvl1(e.target.value)}
                        required
                    >
                        <option value="" disabled>
                            Выберите категорию
                        </option>
                        {categories.map((c, i) => (
                            <option key={i} value={i}>
                                {c.name}
                            </option>
                        ))}
                    </select>
                </div>

                {/* Фильтры */}
                <div className="grid grid-cols-3 gap-4">
                    <div>
                        <label className="text-center block mb-1 font-medium">Мин. продаж</label>
                        <input
                            type="number"
                            min="0"
                            value={minSales}
                            onChange={(e) => setMinSales(Number(e.target.value))}
                            className="w-full p-2 border rounded"
                            required
                        />
                    </div>
                    <div>
                        <label className="text-center block mb-1 font-medium">Макс. продаж</label>
                        <input
                            type="number"
                            min="0"
                            value={maxSales}
                            onChange={(e) => setMaxSales(e.target.value)}
                            className="w-full p-2 border rounded"
                        />
                    </div>
                    <div>
                        <label className="text-center block mb-1 font-medium">
                            Лимит
                        </label>

                        <input
                            type="number"
                            min="0"
                            max="1000"
                            value={limit}
                            onChange={(e) => setLimit(Math.max(0, Number(e.target.value)))}
                            className="w-full p-2 border rounded"
                            required
                        />
                    </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <label className="text-center block mb-1 font-medium">
                            Мин. дата регистрации
                        </label>
                        <input
                            type="date"
                            value={regDate}
                            onChange={(e) => setRegDate(e.target.value)}
                            className="w-full p-2 border rounded"
                            required
                        />
                    </div>
                    <div>
                        <label className="text-center block mb-1 font-medium">
                            Макс. дата регистрации
                        </label>
                        <input
                            type="date"
                            value={maxRegDate}
                            onChange={(e) => setMaxRegDate(e.target.value)}
                            className="w-full p-2 border rounded"
                            required
                        />
                    </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <label className="text-center block mb-1 font-medium">Регионы</label>
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
                    <div>
                        <label className="block mb-1 font-medium">
                            Кол-во страниц
                        </label>
                        <input
                            type="number"
                            min="1"
                            max="50"
                            value={pages}
                            onChange={(e) => setPages(Number(e.target.value))}
                            className="w-full p-2 border rounded"
                            required
                        />
                    </div>
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

            {items.length > 0 && (
                <div
                    className="w-full max-w-xl bg-white rounded-2xl shadow p-6 mt-6 overflow-y-auto"
                    style={{ maxHeight: "70vh" }}
                >
                    <h2 className="text-xl font-semibold mb-4">
                        Найдено: {items.length}
                    </h2>
                    <ul className="overflow-y-auto divide-y pr-2 text-sm break-words">
                        {items.map((it, idx) => (
                            <li key={idx} className="py-2">
                                <div>
                                    <strong>Магазин:</strong> {it.store_name || it.trademark}
                                </div>
                                <div>
                                    <strong>ИНН:</strong> {it.inn}
                                </div>
                                {it.ogrn && (
                                    <div>
                                        <strong>ОГРН:</strong> {it.ogrn}
                                    </div>
                                )}
                                {it.ogrnip && (
                                    <div>
                                        <strong>ОГРНИП:</strong> {it.ogrnip}
                                    </div>
                                )}
                                <div>
                                    <strong>Налоговый орган:</strong> {it.tax_office}
                                </div>
                                <div>
                                    <strong>URL:</strong>{" "}
                                    <a
                                        href={it.url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                    >
                                        {it.url}
                                    </a>
                                </div>
                                <div>
                                    <strong>Дата рег.:</strong>{" "}
                                    {new Date(it.reg_date).toLocaleString()}
                                </div>
                                <div>
                                    <strong>Продаж:</strong> {it.saleCount}
                                </div>
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
