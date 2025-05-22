// src/App.jsx

import { useState, useEffect, useRef } from "react";
import Cookies from "js-cookie";

// Убрали зависимость от внешней библиотеки jwt-decode
import categories from "./categories.json";
import codes from "./codes.json";
import Auth from "./components/Auth.jsx";
import ParserWB from "./components/ParserWB.jsx";
import ParserWBAll from "./components/ParserWBAll.jsx";
import SearchPage from "./pages/SearchPage.jsx";

function parseJwt(token) {
    try {
        const base64Url = token.split('.')[1];
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        const jsonPayload = decodeURIComponent(
            atob(base64)
                .split('')
                .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
                .join('')
        );
        return JSON.parse(jsonPayload);
    } catch {
        return {};
    }
}

export default function App() {
    const [token, setToken] = useState(Cookies.get("access_token") || "");
    const [activeParser, setActiveParser] = useState("wb");
    const [balance, setBalance] = useState(null);
    const [loadingBalance, setLoadingBalance] = useState(false);
    const logoutTimerRef = useRef(null);

    const API_BASE =
        import.meta.env.VITE_API_BASE ||
        `http://${window.location.hostname}:8000`;

    // Управление токеном в куки
    useEffect(() => {
        if (token) {
            Cookies.set("access_token", token, { expires: 7, sameSite: "lax" });
        } else {
            Cookies.remove("access_token");
        }
    }, [token]);

    // Автоматический логаут по истечении JWT
    useEffect(() => {
        if (logoutTimerRef.current) {
            clearTimeout(logoutTimerRef.current);
            logoutTimerRef.current = null;
        }
        if (token) {
            const { exp } = parseJwt(token);
            const msUntilExpiry = exp ? exp * 1000 - Date.now() : 0;
            if (msUntilExpiry > 0) {
                logoutTimerRef.current = window.setTimeout(handleLogout, msUntilExpiry);
            } else {
                handleLogout();
            }
        }
        return () => {
            if (logoutTimerRef.current) clearTimeout(logoutTimerRef.current);
        };
    }, [token]);

    // Подгрузка баланса каждую секунду 15
    useEffect(() => {
        let mounted = true;

        async function fetchBalance() {
            setLoadingBalance(true);
            try {
                const res = await fetch(`${API_BASE}/usersbox/balance`, {
                    headers: { Authorization: `Bearer ${token}` },
                });
                if (!res.ok) throw new Error(`HTTP ${res.status}`);
                const json = await res.json();
                if (mounted) {
                    setBalance(json.data);
                }
            } catch (e) {
                console.error("Ошибка получения баланса:", e);
            } finally {
                if (mounted) setLoadingBalance(false);
            }
        }

        fetchBalance();
        const interval = setInterval(fetchBalance, 15000);
        return () => {
            mounted = false;
            clearInterval(interval);
        };
    }, [token]);

    function handleLogin(newToken) {
        setToken(newToken);
    }

    function handleLogout() {
        setToken("");
        setActiveParser("wb");
    }

    if (!token) {
        return <Auth onLogin={handleLogin} />;
    }

    return (
        <div className="flex h-screen">
            <aside className="fixed top-0 left-0 z-50 w-60 bg-white shadow h-screen p-4 flex flex-col justify-between">
                <div>
                    {/* Баланс над списком действий */}
                    <div className="mb-4 text-sm text-gray-700">
                        Баланс: {loadingBalance
                            ? `${balance} руб.`
                            : balance !== null
                                ? `${balance} руб.`
                                : "Баланс недоступен"}
                    </div>
                    {/*<h3 className="font-semibold mb-4"></h3>*/}
                    <ul className="space-y-2">
                        <li>
                            <button
                                onClick={() => setActiveParser("wb")}
                                className={`w-full text-left p-2 rounded ${
                                    activeParser === "wb" ? "bg-violet-100" : "hover:bg-gray-100"
                                }`}
                            >
                                WB (категории)
                            </button>
                        </li>
                        <li>
                            <button
                                onClick={() => setActiveParser("wbAll")}
                                className={`w-full text-left p-2 rounded ${
                                    activeParser === "wbAll" ? "bg-violet-100" : "hover:bg-gray-100"
                                }`}
                            >
                                WB (каталог)
                            </button>
                        </li>
                        <li>
                            <button
                                onClick={() => setActiveParser("search")}
                                className={`w-full text-left p-2 rounded ${
                                    activeParser === "search" ? "bg-violet-100" : "hover:bg-gray-100"
                                }`}
                            >
                                Поиск по БД
                            </button>
                        </li>
                    </ul>
                </div>
                <button
                    onClick={handleLogout}
                    className="w-full text-left p-2 mt-4 rounded bg-red-100 hover:bg-red-200"
                >
                    Выйти
                </button>
            </aside>

            <main className="flex-1 overflow-auto">
                {activeParser === "wb" && (
                    <ParserWB
                        token={token}
                        onLogout={handleLogout}
                        categories={categories}
                        codes={codes}
                    />
                )}
                {activeParser === "wbAll" && (
                    <ParserWBAll
                        token={token}
                        onLogout={handleLogout}
                        categories={categories}
                        codes={codes}
                    />
                )}
                {activeParser === "search" && (
                    <SearchPage token={token} />
                )}
            </main>
        </div>
    );
}
