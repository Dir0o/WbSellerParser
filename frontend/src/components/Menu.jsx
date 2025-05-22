import React from "react";

export default function Menu({ selected, onSelect }) {
    return (
        <div className="w-60 bg-white shadow h-screen p-4 flex flex-col gap-2">
            <button
                onClick={() => onSelect("subcat")}
                className={`py-2 px-4 rounded text-left transition ${
                    selected === "subcat"
                        ? "bg-violet-600 text-white"
                        : "hover:bg-gray-100"
                }`}
            >
                По подкатегориям
            </button>
            <button
                onClick={() => onSelect("all")}
                className={`py-2 px-4 rounded text-left transition ${
                    selected === "all"
                        ? "bg-violet-600 text-white"
                        : "hover:bg-gray-100"
                }`}
            >
                По главным категориям
            </button>
        </div>
    );
}
