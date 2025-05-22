// src/utils/debounce.js

export default function debounce(func, wait) {
    let timeout;
    function debounced(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func(...args), wait);
    }
    debounced.cancel = () => clearTimeout(timeout);
    return debounced;
}
