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
          e.preventDefault();
          openModal();
        }}
        className="cursor-pointer text-lg leading-none"
      >
        ⚙
      </span>
    </components.DropdownIndicator>
  );
}

export default function ParserWB({ token, onLogout, categories, codes }) {
  // вместо трёх уровней — массив для произвольной глубины
  const [selectedPath, setSelectedPath] = useState([]);
  const [minSales, setMinSales] = useState(0);
  const [maxSales, setMaxSales] = useState("");
  const [regDate, setRegDate] = useState("");
  const [maxRegDate, setMaxRegDate] = useState("");

  /* ---------- регионы ---------- */
  const [regions, setRegions] = useState([]); // ['77','50',…]
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
  const [limit, setLimit] = useState(0);
  const [lastCollected, setLastCollected] = useState(null);
  const [loading, setLoading] = useState(false);
  const [items, setItems] = useState(null);
  const [error, setError] = useState("");
  const [jobId, setJobId] = useState("");

  const API_BASE =
    import.meta.env.VITE_API_BASE ||
    `http://${window.location.hostname}:8000`;

  // вычисляем список опций для каждого уровня
  const optionsByLevel = [];
  let nodes = categories;
  for (let level = 0; nodes; level++) {
    optionsByLevel.push(nodes);
    const selectedIdx = selectedPath[level];
    if (selectedIdx != null && nodes[selectedIdx]?.childs) {
      nodes = nodes[selectedIdx].childs;
    } else {
      break;
    }
  }

  // функция для получения самого глубокого выбранного узла
  const getDeepest = () => {
    let node = null;
    let arr = categories;
    for (let idx of selectedPath) {
      if (!arr) break;
      node = arr[idx];
      arr = node?.childs;
    }
    return node;
  };

  useEffect(() => {
    const deepest = getDeepest();
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
  }, [
    JSON.stringify(selectedPath),
    minSales,
    maxSales,
    region,
    pages,
    token,
    regionStr,
  ]);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    setItems([]);

    try {
      const deepest = getDeepest();
      if (!deepest) throw new Error("Не выбрана категория");

      const { shard, query } = deepest;
      let startUrl = `${API_BASE}/wb/cat/jobs?${query}`;
      startUrl += `&shard=${shard}`;
      startUrl += `&region_id=${regionStr}`;
      startUrl += `&saleItemCount=${minSales}`;
      startUrl += `&pages=${pages}`;
      if (limit) startUrl += `&limit=${limit}`;
      if (maxSales) startUrl += `&maxSaleCount=${maxSales}`;
      if (regDate) startUrl += `&regDate=${regDate}`;
      if (maxRegDate) startUrl += `&maxRegDate=${maxRegDate}`;

      const startRes = await fetch(startUrl, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!startRes.ok) {
        throw new Error(`Ошибка запуска: HTTP ${startRes.status}`);
      }

      const startJson = await startRes.json();
      const newJobId = startJson.job_id ?? startJson.jobId;
      if (!newJobId) {
        console.error("Некорректный ответ сервера:", startJson);
        throw new Error("Сервер не вернул job_id");
      }
      setJobId(newJobId);

      while (true) {
        await new Promise(r => setTimeout(r, 1000));
        const stRes = await fetch(
          `${API_BASE}/wb/cat/jobs/${newJobId}/status`,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        if (!stRes.ok) {
          throw new Error(`Ошибка статуса: HTTP ${stRes.status}`);
        }
        const { status: s, error: srvError } = await stRes.json();
        if (s === "finished") break;
        if (s === "failed") {
          throw new Error(`Парсинг не удался: ${srvError}`);
        }
      }

      const resRes = await fetch(
        `${API_BASE}/wb/cat/jobs/${newJobId}/result`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (!resRes.ok) {
        throw new Error(`Ошибка получения результата: HTTP ${resRes.status}`);
      }
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
      if (!jobId) {
        throw new Error("Сначала запустите парсинг, чтобы получить job_id");
      }

      const res = await fetch(
        `${API_BASE}/wb/cat/jobs/${jobId}/excel`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (res.status === 202) {
        setError("Excel ещё формируется, попробуйте позже.");
        return;
      }
      if (!res.ok) {
        throw new Error(`Ошибка Excel: HTTP ${res.status}`);
      }

      const blob = await res.blob();
      const blobUrl = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = blobUrl;
      a.download = `sellers_${jobId}.xlsx`;
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

        {/* Динамические селекты для категорий */}
        {optionsByLevel.map((opts, lvl) => (
          <div key={lvl}>
            <label className="block mb-1 font-medium">
              {lvl === 0 ? "Категория" : "Подкатегория"}
            </label>
            <select
              className="w-full p-2 border rounded"
              value={selectedPath[lvl] ?? ""}
              onChange={e => {
                const idx = e.target.value;
                setSelectedPath(path => {
                  const newPath = path.slice(0, lvl);
                  newPath[lvl] = idx;
                  return newPath;
                });
              }}
              required
            >
              <option value="" disabled>Выберите категорию</option>
              {opts.map((c, i) => (
                <option key={i} value={i}>{c.name}</option>
              ))}
            </select>
          </div>
        ))}

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
            menuIsOpen={false}
            closeMenuOnSelect={false}
            isSearchable={false}
            placeholder="Нажмите ⚙ чтобы выбрать"
            components={{
              DropdownIndicator: GearIndicator,
              IndicatorSeparator: () => null,
            }}
            openModal={() => { setTempSel(regions); setIsOpen(true); }}
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
                        <label key={value} className="flex items-center gap-2 select-none">
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
                  <strong>Телефон:</strong>{" "}
                  {Array.isArray(it.phone)
                    ? (it.phone.length ? it.phone.join(", ") : "Не найдено")
                    : (it.phone || "Не найдено")}
                </div>
                <div>
                  <strong>Почта:</strong>{" "}
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
