/**
 * Reusable UI Components for Prompt Companion
 * 
 * This module provides common UI building blocks used throughout the application.
 * Components are designed to be lightweight, reusable, and consistent.
 */

import { $el } from "../../../../scripts/ui.js";

/**
 * Create a standardized button element
 * @param {Object} options - Button configuration
 * @param {string} options.text - Button text
 * @param {Function} options.onClick - Click handler
 * @param {string} [options.variant="primary"] - Button style variant
 * @param {boolean} [options.disabled=false] - Disabled state
 * @param {Object} [options.style={}] - Additional styles
 * @returns {HTMLElement} Button element
 */
export function createButton({ text, onClick, variant = "primary", disabled = false, style = {} }) {
    const variants = {
        primary: { backgroundColor: "#007bff", color: "white" },
        secondary: { backgroundColor: "#6c757d", color: "white" },
        success: { backgroundColor: "#28a745", color: "white" },
        warning: { backgroundColor: "#ffc107", color: "white" },
        danger: { backgroundColor: "#dc3545", color: "white" }
    };
    
    const baseStyle = {
        padding: "6px 12px",
        border: "none",
        borderRadius: "4px",
        cursor: disabled ? "not-allowed" : "pointer",
        fontSize: "11px",
        opacity: disabled ? 0.6 : 1,
        ...variants[variant],
        ...style
    };
    
    return $el("button", {
        type: "button",
        textContent: text,
        onclick: disabled ? null : onClick,
        disabled,
        style: baseStyle
    });
}

/**
 * Create a scrollable list container
 * @param {Object} options - List configuration
 * @param {string} [options.height="200px"] - List height
 * @param {Function} [options.onItemClick] - Item click handler
 * @param {Object} [options.style={}] - Additional styles
 * @returns {HTMLElement} List container element
 */
export function createScrollableList({ height = "200px", onItemClick, style = {} }) {
    const baseStyle = {
        height,
        overflowY: "auto",
        border: "1px solid #444",
        borderRadius: "4px",
        backgroundColor: "#2a2a2a",
        ...style
    };
    
    const listElement = $el("div", { style: baseStyle });
    
    // Store click handler for later use
    if (onItemClick) {
        listElement.addEventListener("click", (e) => {
            const item = e.target.closest("[data-item]");
            if (item) {
                onItemClick(item.dataset.item, item, e);
            }
        });
    }
    
    return listElement;
}

/**
 * Create a list item element
 * @param {Object} options - Item configuration
 * @param {string} options.text - Item display text
 * @param {string} options.value - Item value
 * @param {boolean} [options.selected=false] - Selected state
 * @param {Object} [options.style={}] - Additional styles
 * @returns {HTMLElement} List item element
 */
export function createListItem({ text, value, selected = false, style = {} }) {
    const baseStyle = {
        padding: "8px 12px",
        cursor: "pointer",
        borderBottom: "1px solid #444",
        backgroundColor: selected ? "#007bff" : "transparent",
        color: selected ? "white" : "#ccc",
        ...style
    };
    
    const item = $el("div", {
        textContent: text,
        "data-item": value,
        style: baseStyle
    });
    
    // Add hover effects
    item.addEventListener("mouseenter", () => {
        if (!selected) {
            item.style.backgroundColor = "#444";
        }
    });
    
    item.addEventListener("mouseleave", () => {
        if (!selected) {
            item.style.backgroundColor = "transparent";
        }
    });
    
    return item;
}

/**
 * Create a form field container
 * @param {Object} options - Field configuration
 * @param {string} options.label - Field label
 * @param {HTMLElement} options.input - Input element
 * @param {string} [options.description] - Help text
 * @param {Object} [options.style={}] - Additional styles
 * @returns {HTMLElement} Field container element
 */
export function createFormField({ label, input, description, style = {} }) {
    const baseStyle = {
        display: "flex",
        flexDirection: "column",
        gap: "4px",
        marginBottom: "12px",
        ...style
    };
    
    const elements = [
        $el("label", {
            textContent: label,
            style: {
                fontSize: "12px",
                fontWeight: "bold",
                color: "#ccc"
            }
        }),
        input
    ];
    
    if (description) {
        elements.push($el("small", {
            textContent: description,
            style: {
                fontSize: "10px",
                color: "#888",
                fontStyle: "italic"
            }
        }));
    }
    
    return $el("div", { style: baseStyle }, elements);
}

/**
 * Create a text input element
 * @param {Object} options - Input configuration
 * @param {string} [options.value=""] - Initial value
 * @param {string} [options.placeholder=""] - Placeholder text
 * @param {boolean} [options.multiline=false] - Multiline textarea
 * @param {Function} [options.onChange] - Change handler
 * @param {Object} [options.style={}] - Additional styles
 * @returns {HTMLElement} Input element
 */
export function createTextInput({ value = "", placeholder = "", multiline = false, onChange, style = {} }) {
    const baseStyle = {
        padding: "6px 8px",
        border: "1px solid #444",
        borderRadius: "4px",
        backgroundColor: "#1a1a1a",
        color: "#ccc",
        fontSize: "12px",
        outline: "none",
        ...style
    };
    
    if (multiline) {
        baseStyle.resize = "vertical";
        baseStyle.minHeight = "60px";
    }
    
    const input = $el(multiline ? "textarea" : "input", {
        value,
        placeholder,
        style: baseStyle
    });
    
    if (!multiline) {
        input.type = "text";
    }
    
    if (onChange) {
        input.addEventListener("input", (e) => onChange(e.target.value, e));
    }
    
    // Focus styling
    input.addEventListener("focus", () => {
        input.style.borderColor = "#007bff";
    });
    
    input.addEventListener("blur", () => {
        input.style.borderColor = "#444";
    });
    
    return input;
}

/**
 * Create a status message element
 * @param {Object} options - Status configuration
 * @param {string} [options.message=""] - Status message
 * @param {string} [options.type="info"] - Message type (info, success, warning, error)
 * @param {Object} [options.style={}] - Additional styles
 * @returns {HTMLElement} Status element
 */
export function createStatusMessage({ message = "", type = "info", style = {} }) {
    const typeColors = {
        info: "#17a2b8",
        success: "#28a745", 
        warning: "#ffc107",
        error: "#dc3545"
    };
    
    const baseStyle = {
        textAlign: "center",
        fontSize: "12px",
        padding: "8px",
        borderRadius: "4px",
        backgroundColor: `${typeColors[type]}20`,
        color: typeColors[type],
        border: `1px solid ${typeColors[type]}40`,
        ...style
    };
    
    const element = $el("div", {
        textContent: message,
        style: baseStyle
    });
    
    // Auto-hide success messages after 3 seconds
    if (type === "success" && message) {
        setTimeout(() => {
            element.style.opacity = "0";
            element.style.transition = "opacity 0.3s";
            setTimeout(() => {
                element.textContent = "";
                element.style.opacity = "1";
            }, 300);
        }, 3000);
    }
    
    return element;
}

/**
 * Create a loading spinner element
 * @param {Object} [options={}] - Spinner configuration
 * @param {string} [options.size="20px"] - Spinner size
 * @param {string} [options.color="#007bff"] - Spinner color
 * @returns {HTMLElement} Spinner element
 */
export function createLoadingSpinner({ size = "20px", color = "#007bff" } = {}) {
    return $el("div", {
        style: {
            width: size,
            height: size,
            border: `2px solid transparent`,
            borderTop: `2px solid ${color}`,
            borderRadius: "50%",
            animation: "spin 1s linear infinite",
            margin: "0 auto"
        }
    });
}

/**
 * Create a dialog header
 * @param {Object} options - Header configuration
 * @param {string} options.title - Dialog title
 * @param {Function} [options.onClose] - Close button handler
 * @returns {HTMLElement} Header element
 */
export function createDialogHeader({ title, onClose }) {
    const elements = [
        $el("h2", {
            textContent: title,
            style: {
                margin: "0",
                fontSize: "18px",
                fontWeight: "bold",
                color: "#fff"
            }
        })
    ];
    
    if (onClose) {
        elements.push(createButton({
            text: "×",
            onClick: onClose,
            variant: "secondary",
            style: {
                minWidth: "30px",
                padding: "4px 8px",
                fontSize: "16px"
            }
        }));
    }
    
    return $el("div", {
        style: {
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: "16px",
            borderBottom: "1px solid #444",
            backgroundColor: "#333"
        }
    }, elements);
}

// Add CSS animation for spinner
if (!document.querySelector("#prompt-companion-styles")) {
    const style = document.createElement("style");
    style.id = "prompt-companion-styles";
    style.textContent = `
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    `;
    document.head.appendChild(style);
}