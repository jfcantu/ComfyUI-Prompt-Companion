/**
 * Base Dialog Class for Prompt Companion
 * 
 * Provides common dialog functionality that can be extended by specific dialogs.
 * Handles modal behavior, keyboard navigation, and consistent styling.
 */

import { ComfyDialog } from "../../../../scripts/ui.js";
import { createDialogHeader, createStatusMessage, createLoadingSpinner } from "./ui-components.js";

/**
 * Base class for all Prompt Companion dialogs
 * @extends ComfyDialog
 */
export class BaseDialog extends ComfyDialog {
    /**
     * Create a new base dialog
     * @param {Object} options - Dialog configuration
     * @param {string} options.title - Dialog title
     * @param {string} [options.className] - Additional CSS class
     * @param {Object} [options.size] - Dialog size {width, height}
     * @param {boolean} [options.modal=true] - Modal behavior
     */
    constructor({ title, className, size, modal = true }) {
        super();
        
        this.title = title;
        this.className = className;
        this.size = size || { width: "800px", height: "600px" };
        this.modal = modal;
        
        // State management
        this.isLoading = false;
        this.lastStatus = null;
        
        // Initialize dialog
        this.setupDialog();
        this.setupKeyboardHandlers();
    }
    
    /**
     * Set up basic dialog structure and styling
     * @private
     */
    setupDialog() {
        if (this.className) {
            this.element.classList.add(this.className);
        }
        
        // Apply consistent styling
        Object.assign(this.element.style, {
            backgroundColor: "#2a2a2a",
            border: "1px solid #444",
            borderRadius: "8px",
            boxShadow: "0 4px 20px rgba(0,0,0,0.5)",
            color: "#ccc",
            fontFamily: "system-ui, -apple-system, sans-serif",
            maxWidth: "90vw",
            maxHeight: "90vh",
            minWidth: this.size.width,
            minHeight: this.size.height
        });
    }
    
    /**
     * Set up keyboard event handlers
     * @private
     */
    setupKeyboardHandlers() {
        this.keyHandler = (e) => {
            switch (e.key) {
                case "Escape":
                    if (this.onEscape) {
                        this.onEscape();
                    } else {
                        this.close();
                    }
                    break;
                case "Enter":
                    if (e.ctrlKey && this.onCtrlEnter) {
                        this.onCtrlEnter();
                    }
                    break;
                default:
                    if (this.onKeyDown) {
                        this.onKeyDown(e);
                    }
            }
        };
    }
    
    /**
     * Show the dialog
     * @param {HTMLElement} [content] - Dialog content element
     */
    show(content) {
        // Add keyboard handler
        document.addEventListener("keydown", this.keyHandler);
        
        // Call parent show method
        super.show(content);
        
        // Focus management
        this.focus();
    }
    
    /**
     * Close the dialog
     */
    close() {
        // Remove keyboard handler
        document.removeEventListener("keydown", this.keyHandler);
        
        // Call cleanup if defined
        if (this.cleanup) {
            this.cleanup();
        }
        
        // Call parent close method
        super.close();
    }
    
    /**
     * Set focus to the first focusable element
     */
    focus() {
        const focusableElements = this.element.querySelectorAll(
            'button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled])'
        );
        
        if (focusableElements.length > 0) {
            focusableElements[0].focus();
        }
    }
    
    /**
     * Create dialog header with title and optional close button
     * @param {boolean} [showCloseButton=true] - Show close button
     * @returns {HTMLElement} Header element
     */
    createHeader(showCloseButton = true) {
        return createDialogHeader({
            title: this.title,
            onClose: showCloseButton ? () => this.close() : null
        });
    }
    
    /**
     * Create status message area
     * @returns {HTMLElement} Status element
     */
    createStatusArea() {
        this.statusElement = createStatusMessage({});
        return this.statusElement;
    }
    
    /**
     * Update status message
     * @param {string} message - Status message
     * @param {string} [type="info"] - Message type
     */
    updateStatus(message, type = "info") {
        if (this.statusElement) {
            this.statusElement.textContent = message;
            this.statusElement.className = `status-${type}`;
            
            // Update styling based on type
            const typeColors = {
                info: "#17a2b8",
                success: "#28a745", 
                warning: "#ffc107",
                error: "#dc3545"
            };
            
            const color = typeColors[type];
            Object.assign(this.statusElement.style, {
                backgroundColor: `${color}20`,
                color: color,
                borderColor: `${color}40`
            });
        }
        
        this.lastStatus = { message, type };
    }
    
    /**
     * Show loading state
     * @param {string} [message="Loading..."] - Loading message
     */
    showLoading(message = "Loading...") {
        this.isLoading = true;
        
        if (!this.loadingOverlay) {
            this.loadingOverlay = document.createElement("div");
            Object.assign(this.loadingOverlay.style, {
                position: "absolute",
                top: "0",
                left: "0",
                right: "0",
                bottom: "0",
                backgroundColor: "rgba(0,0,0,0.7)",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                gap: "16px",
                zIndex: "1000"
            });
            
            this.loadingOverlay.appendChild(createLoadingSpinner({ size: "32px" }));
            this.loadingOverlay.appendChild(document.createElement("div"));
            this.loadingOverlay.lastChild.textContent = message;
            this.loadingOverlay.lastChild.style.color = "#ccc";
            
            this.element.style.position = "relative";
            this.element.appendChild(this.loadingOverlay);
        } else {
            this.loadingOverlay.style.display = "flex";
            this.loadingOverlay.lastChild.textContent = message;
        }
        
        // Disable all interactive elements
        this.toggleInteractiveElements(false);
    }
    
    /**
     * Hide loading state
     */
    hideLoading() {
        this.isLoading = false;
        
        if (this.loadingOverlay) {
            this.loadingOverlay.style.display = "none";
        }
        
        // Re-enable interactive elements
        this.toggleInteractiveElements(true);
    }
    
    /**
     * Toggle interactive elements
     * @param {boolean} enabled - Enable or disable
     * @private
     */
    toggleInteractiveElements(enabled) {
        const elements = this.element.querySelectorAll('button, input, textarea, select');
        elements.forEach(el => {
            el.disabled = !enabled;
            el.style.opacity = enabled ? "1" : "0.6";
        });
    }
    
    /**
     * Confirm action with user
     * @param {string} message - Confirmation message
     * @param {string} [title="Confirm"] - Confirmation dialog title
     * @returns {Promise<boolean>} User confirmation
     */
    async confirm(message, title = "Confirm") {
        return new Promise((resolve) => {
            if (window.confirm(`${title}: ${message}`)) {
                resolve(true);
            } else {
                resolve(false);
            }
        });
    }
    
    /**
     * Prompt user for input
     * @param {string} message - Prompt message
     * @param {string} [title="Input"] - Prompt dialog title
     * @param {string} [defaultValue=""] - Default input value
     * @returns {Promise<string|null>} User input or null if cancelled
     */
    async prompt(message, title = "Input", defaultValue = "") {
        return new Promise((resolve) => {
            const result = window.prompt(`${title}: ${message}`, defaultValue);
            resolve(result);
        });
    }
    
    /**
     * Handle validation errors
     * @param {Array|string} errors - Validation errors
     */
    handleValidationErrors(errors) {
        const errorList = Array.isArray(errors) ? errors : [errors];
        const message = errorList.join(", ");
        this.updateStatus(`Validation Error: ${message}`, "error");
    }
    
    /**
     * Handle API errors
     * @param {Error|Object} error - Error object
     */
    handleApiError(error) {
        console.error("API Error:", error);
        
        let message = "An unexpected error occurred";
        if (error.message) {
            message = error.message;
        } else if (error.errors && Array.isArray(error.errors)) {
            message = error.errors.join(", ");
        }
        
        this.updateStatus(`Error: ${message}`, "error");
    }
    
    /**
     * Safely execute an async operation with loading state
     * @param {Function} operation - Async operation to execute
     * @param {string} [loadingMessage="Processing..."] - Loading message
     * @returns {Promise<any>} Operation result
     */
    async safeExecute(operation, loadingMessage = "Processing...") {
        try {
            this.showLoading(loadingMessage);
            const result = await operation();
            return result;
        } catch (error) {
            this.handleApiError(error);
            throw error;
        } finally {
            this.hideLoading();
        }
    }
    
    /**
     * Cleanup method called when dialog closes
     * Override in subclasses for custom cleanup
     */
    cleanup() {
        // Override in subclasses
    }
    
    /**
     * Handle Escape key
     * Override in subclasses for custom behavior
     */
    onEscape() {
        // Override in subclasses
    }
    
    /**
     * Handle Ctrl+Enter key combination
     * Override in subclasses for custom behavior
     */
    onCtrlEnter() {
        // Override in subclasses
    }
    
    /**
     * Handle general keydown events
     * Override in subclasses for custom behavior
     * @param {KeyboardEvent} event - Keyboard event
     */
    onKeyDown(event) {
        // Override in subclasses
    }
}