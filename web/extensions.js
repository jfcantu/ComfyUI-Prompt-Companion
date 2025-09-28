/*
 * ComfyUI-Prompt-Companion Extension Integration
 * 
 * Clean production implementation that integrates the Prompt Companion system
 * with ComfyUI. Registers extension, loads CSS, sets up context menus,
 * and initializes dialog components.
 */

import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";

// Import dialog and tree view components
import "./edit_dialog.js";
import "./tree_view.js";

/**
 * Load CSS styles for the prompt companion
 */
function loadCSS() {
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.type = 'text/css';
    link.href = '/extensions/ComfyUI-Prompt-Companion/prompt_companion.css';
    document.head.appendChild(link);
}

/**
 * Initialize the prompt companion system
 */
function initializePromptCompanion() {
    // Load CSS styles
    loadCSS();
    
    // Initialize global namespace
    if (!window.PromptCompanion) {
        window.PromptCompanion = {};
    }
    
    // Set up API endpoints
    setupAPIEndpoints();
}

/**
 * Set up API endpoints for frontend-backend communication
 */
function setupAPIEndpoints() {
    window.PromptCompanion.api = {
        async getSubprompts() {
            try {
                const response = await api.fetchApi("/prompt_companion/subprompts");
                if (response.ok) {
                    return await response.json();
                }
                return {};
            } catch (error) {
                console.error("Failed to fetch subprompts:", error);
                return {};
            }
        },
        
        async saveSubprompt(subprompt) {
            try {
                const method = subprompt.id ? "PUT" : "POST";
                const url = subprompt.id ? 
                    `/prompt_companion/subprompts/${subprompt.id}` : 
                    "/prompt_companion/subprompts";
                
                const response = await api.fetchApi(url, {
                    method: method,
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(subprompt)
                });
                
                return response.ok;
            } catch (error) {
                console.error("Failed to save subprompt:", error);
                return false;
            }
        },
        
        async deleteSubprompt(id) {
            try {
                const response = await api.fetchApi(`/prompt_companion/subprompts/${id}`, {
                    method: "DELETE"
                });
                return response.ok;
            } catch (error) {
                console.error("Failed to delete subprompt:", error);
                return false;
            }
        },
        
        async getFolders() {
            try {
                const response = await api.fetchApi("/prompt_companion/folders");
                if (response.ok) {
                    return await response.json();
                }
                return [];
            } catch (error) {
                console.error("Failed to fetch folders:", error);
                return [];
            }
        }
    };

    // Add autosuggest functionality
    window.PromptCompanion.setupAutosuggest = setupAutosuggest;
}

/**
 * Set up autosuggest functionality for subprompt selection inputs
 */
function setupAutosuggest() {
    // CSS for autosuggest dropdown
    const style = document.createElement('style');
    style.textContent = `
        .autosuggest-container {
            position: relative;
            display: inline-block;
        }
        .autosuggest-dropdown {
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: #2a2a2a;
            border: 1px solid #555;
            border-top: none;
            max-height: 200px;
            overflow-y: auto;
            z-index: 1000;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        }
        .autosuggest-item {
            padding: 8px 12px;
            cursor: pointer;
            color: #fff;
            border-bottom: 1px solid #444;
        }
        .autosuggest-item:hover,
        .autosuggest-item.selected {
            background: #4a5568;
        }
        .autosuggest-item.no-results {
            color: #888;
            font-style: italic;
            cursor: default;
        }
        .autosuggest-item.no-results:hover {
            background: transparent;
        }
    `;
    document.head.appendChild(style);

    // Cache for subprompt options
    let cachedOptions = null;
    let cacheTimestamp = 0;
    const CACHE_DURATION = 30000; // 30 seconds

    async function getCachedSubpromptOptions() {
        const now = Date.now();
        if (!cachedOptions || (now - cacheTimestamp) > CACHE_DURATION) {
            try {
                const subprompts = await window.PromptCompanion.api.getSubprompts();
                cachedOptions = ["None"];
                
                // Convert subprompts array to options with folder paths
                if (Array.isArray(subprompts)) {
                    subprompts.forEach(subprompt => {
                        if (subprompt.folder_path && subprompt.folder_path.trim()) {
                            cachedOptions.push(`${subprompt.folder_path}/${subprompt.name}`);
                        } else {
                            cachedOptions.push(subprompt.name);
                        }
                    });
                }
                
                // Sort options (keeping "None" first)
                const sorted = ["None", ...cachedOptions.slice(1).sort()];
                cachedOptions = sorted;
                cacheTimestamp = now;
            } catch (error) {
                console.error("Failed to fetch subprompt options:", error);
                cachedOptions = ["None"];
            }
        }
        return cachedOptions;
    }

    function filterOptions(options, query) {
        if (!query || query.toLowerCase() === 'none') {
            return options.slice(0, 10); // Show first 10 options
        }
        
        const lowerQuery = query.toLowerCase();
        const filtered = options.filter(option =>
            option.toLowerCase().includes(lowerQuery)
        ).slice(0, 10); // Limit to 10 results

        return filtered.length > 0 ? filtered : ["No matches found"];
    }

    function createAutosuggestDropdown() {
        const dropdown = document.createElement('div');
        dropdown.className = 'autosuggest-dropdown';
        dropdown.style.display = 'none';
        return dropdown;
    }

    function showSuggestions(input, dropdown, options, query) {
        const filtered = filterOptions(options, query);
        dropdown.innerHTML = '';
        
        filtered.forEach((option, index) => {
            const item = document.createElement('div');
            item.className = 'autosuggest-item';
            item.textContent = option;
            
            if (option === "No matches found") {
                item.classList.add('no-results');
            } else {
                item.addEventListener('click', () => {
                    input.value = option;
                    dropdown.style.display = 'none';
                    // Trigger input event to update the widget
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                });
            }
            
            dropdown.appendChild(item);
        });
        
        dropdown.style.display = filtered.length > 0 ? 'block' : 'none';
    }

    function hideSuggestions(dropdown) {
        setTimeout(() => {
            dropdown.style.display = 'none';
        }, 150); // Small delay to allow clicks
    }

    async function enhanceTextInput(input) {
        // Skip if already enhanced
        if (input.hasAutosuggest) return;
        input.hasAutosuggest = true;

        // Wrap input in container
        const container = document.createElement('div');
        container.className = 'autosuggest-container';
        input.parentNode.insertBefore(container, input);
        container.appendChild(input);

        // Create dropdown
        const dropdown = createAutosuggestDropdown();
        container.appendChild(dropdown);

        let selectedIndex = -1;

        // Handle input events
        input.addEventListener('input', async (e) => {
            const query = e.target.value;
            const options = await getCachedSubpromptOptions();
            selectedIndex = -1;
            showSuggestions(input, dropdown, options, query);
        });

        // Handle focus
        input.addEventListener('focus', async () => {
            const query = input.value;
            const options = await getCachedSubpromptOptions();
            showSuggestions(input, dropdown, options, query);
        });

        // Handle blur
        input.addEventListener('blur', () => {
            hideSuggestions(dropdown);
        });

        // Handle keyboard navigation
        input.addEventListener('keydown', (e) => {
            const items = dropdown.querySelectorAll('.autosuggest-item:not(.no-results)');
            
            switch (e.key) {
                case 'ArrowDown':
                    e.preventDefault();
                    selectedIndex = Math.min(selectedIndex + 1, items.length - 1);
                    updateSelection(items, selectedIndex);
                    break;
                case 'ArrowUp':
                    e.preventDefault();
                    selectedIndex = Math.max(selectedIndex - 1, -1);
                    updateSelection(items, selectedIndex);
                    break;
                case 'Enter':
                    e.preventDefault();
                    if (selectedIndex >= 0 && items[selectedIndex]) {
                        input.value = items[selectedIndex].textContent;
                        dropdown.style.display = 'none';
                        input.dispatchEvent(new Event('input', { bubbles: true }));
                    }
                    break;
                case 'Escape':
                    dropdown.style.display = 'none';
                    selectedIndex = -1;
                    break;
            }
        });

        function updateSelection(items, index) {
            items.forEach((item, i) => {
                item.classList.toggle('selected', i === index);
            });
        }
    }

    // Function to enhance all subprompt selection inputs
    window.PromptCompanion.enhanceSubpromptInputs = function() {
        // Find all canvas nodes and check their widgets
        if (app.graph && app.graph._nodes) {
            app.graph._nodes.forEach(node => {
                if (isPromptCompanionNode(node) && node.widgets) {
                    node.widgets.forEach(widget => {
                        if (widget.name === "subprompt_selection" && widget.element) {
                            enhanceTextInput(widget.element);
                        }
                    });
                }
            });
        }
        
        // Also check for any input elements that might have been missed
        const inputs = document.querySelectorAll('input[type="text"], input.comfy-text-input');
        inputs.forEach(input => {
            // Check if this input has a parent that suggests it's a subprompt selection
            const parentNode = input.closest('[data-node-type]') || input.closest('.comfy-widget');
            if (parentNode) {
                // Look for widget name or aria-label
                const widgetName = input.name || input.getAttribute('data-widget') || input.getAttribute('aria-label');
                if (widgetName && widgetName.includes('subprompt_selection')) {
                    enhanceTextInput(input);
                }
            }
        });
    };

    return {
        enhanceTextInput,
        getCachedSubpromptOptions
    };
}

/**
 * Set up context menu integration for prompt companion nodes
 */
function setupContextMenus() {
    if (typeof LiteGraph === 'undefined' || typeof LiteGraph.ContextMenu === 'undefined') {
        // Try to set up later
        setTimeout(() => {
            if (typeof LiteGraph !== 'undefined' && typeof LiteGraph.ContextMenu !== 'undefined') {
                setupContextMenus();
            }
        }, 2000);
        return;
    }
    
    // Store the original ContextMenu constructor
    const originalContextMenu = LiteGraph.ContextMenu;
    
    // Override the ContextMenu constructor
    LiteGraph.ContextMenu = function(values, options) {
        // Ensure values is an array
        if (!values) {
            values = [];
        }
        
        // Check if this is a prompt companion node
        const isPromptNodeByNode = options && options.node && isPromptCompanionNode(options.node);
        const isPromptNodeByTitle = options && options.title && isPromptCompanionNodeByTitle(options.title);
        const isPromptNode = isPromptNodeByNode || isPromptNodeByTitle;
        
        if (isPromptNode) {
            // Add separator if there are existing items
            if (values.length > 0) {
                values.push(null);
            }
            
            // Add "Edit Subprompts" menu item
            values.push({
                content: "Edit Subprompts",
                callback: () => {
                    if (window.PromptCompanion && window.PromptCompanion.showEditDialog) {
                        window.PromptCompanion.showEditDialog();
                    }
                }
            });
        }
        
        // Call the original constructor
        return originalContextMenu.call(this, values, options);
    };
    
    // Preserve the prototype
    LiteGraph.ContextMenu.prototype = originalContextMenu.prototype;
}

/**
 * Check if a node is a prompt companion node
 */
function isPromptCompanionNode(node) {
    const promptCompanionNodes = [
        "PromptCompanion_AddSubprompt",
        "PromptCompanion_SubpromptToStrings",
        "PromptCompanion_StringsToSubprompt",
        "PromptCompanion_LoadCheckpointWithSubprompt"
    ];
    
    return node.type && promptCompanionNodes.includes(node.type);
}

/**
 * Check if a title corresponds to a prompt companion node
 */
function isPromptCompanionNodeByTitle(title) {
    const promptCompanionNodes = [
        "PromptCompanion_AddSubprompt",
        "PromptCompanion_SubpromptToStrings",
        "PromptCompanion_StringsToSubprompt",
        "PromptCompanion_LoadCheckpointWithSubprompt"
    ];
    
    return title && promptCompanionNodes.includes(title);
}

/**
 * Set up keyboard shortcuts
 */
function setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // Ctrl+Shift+P to open Prompt Companion dialog
        if (e.ctrlKey && e.shiftKey && e.key === 'P') {
            e.preventDefault();
            if (window.PromptCompanion && window.PromptCompanion.showEditDialog) {
                window.PromptCompanion.showEditDialog();
            }
        }
    });
}

/**
 * Update node widget options when subprompts change
 *
 * NOTE: This function is DISABLED to prevent conflicts with ComfyUI's native
 * dynamic combo box pattern. The Python backend handles combo box values
 * directly through INPUT_TYPES() function calls.
 */
async function updateNodeWidgetOptions() {
    // DISABLED: Prevented conflicts with Python backend validation
    return;
}

/**
 * Add menu button to ComfyUI interface
 */
function addMenuButton() {
    try {
        if (app.ui && app.ui.menuContainer) {
            const menuButton = document.createElement("button");
            menuButton.textContent = "Subprompts";
            menuButton.onclick = () => {
                if (window.PromptCompanion && window.PromptCompanion.showEditDialog) {
                    window.PromptCompanion.showEditDialog();
                }
            };
            
            // Style the button
            Object.assign(menuButton.style, {
                background: "#4a5568",
                color: "white",
                border: "none",
                padding: "4px 8px",
                margin: "2px",
                borderRadius: "3px",
                cursor: "pointer",
                fontSize: "12px"
            });
            
            // Add hover effects
            menuButton.onmouseover = () => {
                menuButton.style.background = "#2d3748";
            };
            menuButton.onmouseout = () => {
                menuButton.style.background = "#4a5568";
            };
            
            app.ui.menuContainer.appendChild(menuButton);
        }
    } catch (error) {
        // Silently handle menu button creation failure
    }
}

// Register the main extension with ComfyUI
app.registerExtension({
    name: "ComfyUI.PromptCompanion",
    
    async init() {
        // Initialize the prompt companion system
        initializePromptCompanion();
        
        // Set up keyboard shortcuts
        setupKeyboardShortcuts();
        
        // Set up autosuggest functionality
        if (window.PromptCompanion && window.PromptCompanion.setupAutosuggest) {
            window.PromptCompanion.setupAutosuggest();
        }
    },
    
    async setup() {
        // Set up context menus
        setupContextMenus();
        
        // DISABLED: Widget updating conflicts with native Python combo boxes
        // await updateNodeWidgetOptions();
        
        // Add menu button
        addMenuButton();
        
        // Enhance subprompt inputs with autosuggest
        setTimeout(() => {
            if (window.PromptCompanion && window.PromptCompanion.enhanceSubpromptInputs) {
                window.PromptCompanion.enhanceSubpromptInputs();
            }
        }, 1000);
    },
    
    async beforeRegisterNodeDef(nodeType, nodeData) {
        // Handle registration for PromptCompanion nodes
        if (nodeData.name && isPromptCompanionNode({ type: nodeData.name })) {
            
            // Add custom styling for PromptCompanion nodes
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function() {
                if (onNodeCreated) {
                    onNodeCreated.apply(this, arguments);
                }
                
                // Add visual indicator for PromptCompanion nodes
                this.color = "#4a5568";
                this.bgcolor = "#2d3748";
                this.title = this.title || nodeData.display_name || nodeData.name;
                
                // Schedule autosuggest enhancement after widget creation
                setTimeout(() => {
                    if (this.widgets) {
                        this.widgets.forEach(widget => {
                            if (widget.name === "subprompt_selection" && widget.element && !widget.element.hasAutosuggest) {
                                if (window.PromptCompanion && window.PromptCompanion.setupAutosuggest) {
                                    const autosuggest = window.PromptCompanion.setupAutosuggest();
                                    if (autosuggest && autosuggest.enhanceTextInput) {
                                        autosuggest.enhanceTextInput(widget.element);
                                    }
                                }
                            }
                        });
                    }
                }, 100);
            };
            
            // Handle widget updates after execution
            const onExecuted = nodeType.prototype.onExecuted;
            nodeType.prototype.onExecuted = function(message) {
                if (onExecuted) {
                    onExecuted.apply(this, arguments);
                }
                
                // DISABLED: Widget updating conflicts with native Python combo boxes
                // updateNodeWidgetOptions();
            };
            
            // Hook into widget creation to enhance subprompt selection inputs
            const originalAddWidget = nodeType.prototype.addWidget;
            if (originalAddWidget) {
                nodeType.prototype.addWidget = function(type, name, value, callback, options) {
                    const widget = originalAddWidget.call(this, type, name, value, callback, options);
                    
                    if (name === "subprompt_selection" && widget.element) {
                        setTimeout(() => {
                            if (window.PromptCompanion && window.PromptCompanion.setupAutosuggest) {
                                const autosuggest = window.PromptCompanion.setupAutosuggest();
                                if (autosuggest && autosuggest.enhanceTextInput) {
                                    autosuggest.enhanceTextInput(widget.element);
                                }
                            }
                        }, 50);
                    }
                    
                    return widget;
                };
            }
        }
    },
    
    async loadedGraphNode(node) {
        // Called when a node is loaded from a saved workflow
        if (isPromptCompanionNode(node)) {
            // DISABLED: Widget updating conflicts with native Python combo boxes
            // setTimeout(() => updateNodeWidgetOptions(), 100);
        }
    },
    
    async nodeCreated(node) {
        // Called when a new node is created
        if (isPromptCompanionNode(node)) {
            // DISABLED: Widget updating conflicts with native Python combo boxes
            setTimeout(() => {
                // updateNodeWidgetOptions();  // DISABLED
                // Enhance any new subprompt inputs
                if (window.PromptCompanion && window.PromptCompanion.enhanceSubpromptInputs) {
                    window.PromptCompanion.enhanceSubpromptInputs();
                }
            }, 500);
        }
    }
});

// Export for use by other modules
export { initializePromptCompanion, updateNodeWidgetOptions };