/*
 * Clean Edit Dialog Implementation for ComfyUI-Prompt-Companion
 * 
 * This file provides a production-ready dialog for editing subprompts
 * based on the requirements specification. No debugging code included.
 */

import { app } from "../../../scripts/app.js";
import { ComfyDialog, $el } from "../../../scripts/ui.js";
import { api } from "../../../scripts/api.js";

/**
 * Main edit dialog for managing subprompts and folders
 * Uses the proper ComfyUI dialog approach like ComfyUI-Manager
 */
class PromptEditDialog {
    constructor() {
        // Use ComfyDialog instance like ComfyUI-Manager does
        this.dialog = new ComfyDialog();
        
        // Initialize state
        this.currentSubprompt = null;
        this.isEditing = false;
        this.unsavedChanges = false;
        this.treeView = null;
        this.editPanel = null;
        this.pendingPreviewUpdate = null;
        
        // Setup dialog styling like ComfyUI-Manager - optimized for more compact size
        this.dialog.element.style.zIndex = "1100";
        this.dialog.element.style.width = "80%";
        this.dialog.element.style.maxWidth = "1000px";
        this.dialog.element.style.height = "80%";
        this.dialog.element.style.maxHeight = "800px";
        this.dialog.element.style.minWidth = "720px";
        this.dialog.element.style.minHeight = "600px";
        this.dialog.element.style.padding = "0";
        this.dialog.element.style.backgroundColor = "#2d2d2d";
        this.dialog.element.style.border = "1px solid #404040";
        this.dialog.element.style.borderRadius = "8px";
        this.dialog.element.style.boxSizing = "border-box";
        this.dialog.element.style.overflow = "hidden";
        
        this.setupEventHandlers();
        this.setupResizeHandling();
    }
    
    // Get element for compatibility
    get element() {
        return this.dialog.element;
    }
    
    // Remove unused createDialogStructure method since we use createDialogContent
    
    /**
     * Create the edit form for the right panel
     */
    createEditForm() {
        return $el("div", {
            className: "prompt-companion-form-container"
        }, [
            // Positive Prompt
            $el("div", {
                className: "prompt-companion-form-group"
            }, [
                $el("label", { textContent: "Positive Prompt:" }),
                $el("textarea", {
                    id: "subprompt-positive",
                    className: "prompt-companion-input prompt-companion-textarea",
                    placeholder: "Enter positive prompt text..."
                })
            ]),
            
            // Negative Prompt
            $el("div", {
                className: "prompt-companion-form-group"
            }, [
                $el("label", { textContent: "Negative Prompt:" }),
                $el("textarea", {
                    id: "subprompt-negative",
                    className: "prompt-companion-input prompt-companion-textarea",
                    placeholder: "Enter negative prompt text..."
                })
            ]),
            
            // Trigger Words
            $el("div", {
                className: "prompt-companion-form-group"
            }, [
                $el("label", { textContent: "Trigger Words:" }),
                $el("input", {
                    type: "text",
                    id: "subprompt-triggers",
                    className: "prompt-companion-input",
                    placeholder: "word1, word2, word3"
                })
            ]),
            
            // Nested Subprompts with Drag-and-Drop Reordering
            $el("div", {
                className: "prompt-companion-form-group"
            }, [
                $el("label", {
                    textContent: "Nested Subprompts (drag to reorder):",
                    style: {
                        display: "block",
                        marginBottom: "6px",
                        fontWeight: "bold",
                        color: "#ffffff"
                    }
                }),
                $el("div", {
                    className: "prompt-companion-form-group-controls"
                }, [
                    $el("div", {
                        id: "subprompt-nested-list",
                        className: "prompt-companion-nested-list-container",
                        style: {
                            minHeight: "100px",
                            maxHeight: "150px",
                            border: "1px solid #404040",
                            borderRadius: "4px",
                            padding: "4px",
                            backgroundColor: "#1a1a1a",
                            overflow: "auto"
                        }
                    }),
                    $el("div", {
                        className: "prompt-companion-nested-controls"
                    }, [
                        $el("button", {
                            type: "button",
                            className: "prompt-companion-btn prompt-companion-btn-sm",
                            textContent: "Add Subprompt",
                            style: {
                                padding: "6px 12px",
                                backgroundColor: "#007acc",
                                border: "none",
                                borderRadius: "4px",
                                color: "#ffffff",
                                cursor: "pointer",
                                fontSize: "12px",
                                marginTop: "8px"
                            },
                            onclick: () => this.showAddSubpromptDialog()
                        })
                    ])
                ])
            ]),
            
            // Save/Revert buttons in edit panel
            $el("div", {
                className: "prompt-companion-edit-panel-buttons",
                style: {
                    display: "flex",
                    gap: "10px",
                    padding: "15px 0",
                    borderTop: "1px solid #404040",
                    borderBottom: "1px solid #404040",
                    margin: "15px 0"
                }
            }, [
                $el("button", {
                    className: "prompt-companion-btn prompt-companion-btn-primary",
                    textContent: "Save",
                    style: {
                        padding: "8px 16px",
                        backgroundColor: "#28a745",
                        border: "none",
                        borderRadius: "4px",
                        color: "#ffffff",
                        cursor: "pointer",
                        fontSize: "14px"
                    },
                    onclick: async () => { await this.saveSubprompt(); }
                }),
                $el("button", {
                    className: "prompt-companion-btn prompt-companion-btn-secondary",
                    textContent: "Revert",
                    style: {
                        padding: "8px 16px",
                        backgroundColor: "#6c757d",
                        border: "none",
                        borderRadius: "4px",
                        color: "#ffffff",
                        cursor: "pointer",
                        fontSize: "14px"
                    },
                    onclick: () => this.revertChanges()
                })
            ]),
            
            // Validation Messages
            $el("div", {
                id: "validation-messages",
                className: "prompt-companion-validation-messages",
                style: {
                    minHeight: "20px"
                }
            }),
            
            // Preview Section
            $el("div", {
                className: "prompt-companion-form-group"
            }, [
                $el("label", {
                    textContent: "Preview:",
                    style: {
                        display: "block",
                        marginBottom: "6px",
                        fontWeight: "bold",
                        color: "#ffffff"
                    }
                }),
                $el("div", {
                    id: "subprompt-preview",
                    className: "prompt-companion-preview",
                    style: {
                        padding: "12px",
                        backgroundColor: "#1a1a1a",
                        border: "1px solid #404040",
                        borderRadius: "4px",
                        minHeight: "60px",
                        fontSize: "14px",
                        whiteSpace: "pre-wrap"
                    }
                })
            ])
        ]);
    }
    
    /**
     * Setup event handlers
     */
    setupEventHandlers() {
        // Keyboard shortcuts
        this.element.addEventListener("keydown", (e) => {
            if (e.ctrlKey && e.key === "s") {
                e.preventDefault();
                this.saveSubprompt();
            } else if (e.key === "Escape") {
                e.preventDefault();
                this.hide();
            }
        });
        
        // Window resize handling
        window.addEventListener("resize", () => {
            this.handleResize();
        });
        
        // Tree view will be initialized after dialog content is created in show()
    }
    
    /**
     * Setup form event handlers (called after form is created)
     */
    setupFormEventHandlers() {
        const form = this.element.querySelector("#prompt-companion-edit-form");
        if (form) {
            form.addEventListener("input", () => {
                this.markUnsavedChanges(true);
                this.debounceValidation();
                this.debouncePreviewUpdate();
            });
            
            form.addEventListener("change", () => {
                this.markUnsavedChanges(true);
                this.updatePreview().catch(console.error);
            });
        }
        
        // Add direct event handlers to specific fields for more reliable preview updates
        const positiveField = this.element.querySelector("#subprompt-positive");
        const negativeField = this.element.querySelector("#subprompt-negative");
        const triggersField = this.element.querySelector("#subprompt-triggers");
        
        if (positiveField) {
            positiveField.addEventListener("input", () => {
                this.markUnsavedChanges(true);
                this.debouncePreviewUpdate();
            });
        }
        
        if (negativeField) {
            negativeField.addEventListener("input", () => {
                this.markUnsavedChanges(true);
                this.debouncePreviewUpdate();
            });
        }
        
        if (triggersField) {
            triggersField.addEventListener("input", () => {
                this.markUnsavedChanges(true);
                this.debouncePreviewUpdate();
            });
        }
    }
    
    /**
     * Initialize the tree view component
     */
    initializeTreeView() {
        const container = this.element.querySelector("#prompt-companion-tree-container");
        
        if (container && window.PromptCompanion?.initializeTreeView) {
            this.treeView = window.PromptCompanion.initializeTreeView("prompt-companion-tree-container");
            if (this.treeView) {
                this.treeView.onSelectionChange = (item) => this.handleTreeSelectionChange(item);
                
                // Add methods for the tree view to check unsaved changes
                this.treeView.onSelectionChange.checkUnsavedChanges = () => {
                    return this.unsavedChanges;
                };
                
                this.treeView.onSelectionChange.handleUnsavedChanges = async () => {
                    if (!this.unsavedChanges) return true;
                    
                    const result = await this.showUnsavedChangesDialog();
                    
                    if (result === 'cancel') {
                        return false; // Don't proceed with selection change
                    } else if (result === 'save') {
                        // Save current changes before proceeding
                        const saveSuccess = await this.saveSubprompt();
                        return saveSuccess; // Only proceed if save was successful
                    }
                    // If result === 'discard', just continue
                    return true;
                };
            }
        }
    }
    
    /**
     * Handle tree view selection changes with unsaved changes check
     */
    async handleTreeSelectionChange(item) {
        // Note: This method is no longer directly called due to the new approach
        // where unsaved changes are handled in the tree view click handlers
        
        if (item === null) {
            // Deselection - hide edit panel and show placeholder
            this.clearForm();
        } else {
            // Selection of a subprompt - load it for editing
            this.loadSubpromptForEditing(item);
        }
    }
    
    /**
     * Show the dialog using proper ComfyUI approach
     */
    show(subprompt = null) {
        // Clear existing content
        this.element.innerHTML = '';
        
        // Create and add dialog content to the dialog element
        const content = this.createDialogContent();
        this.element.appendChild(content);
        
        // Show using ComfyDialog.show() like ComfyUI-Manager
        this.dialog.show();
        
        if (subprompt) {
            this.loadSubpromptForEditing(subprompt);
        } else {
            this.clearForm();
        }
        
        // Focus first input
        setTimeout(() => {
            const firstInput = this.element.querySelector("input, textarea");
            if (firstInput) firstInput.focus();
        }, 100);
        
        // Initialize tree view AFTER dialog content is created
        this.initializeTreeView();
        
        // Setup form event handlers AFTER form is created
        this.setupFormEventHandlers();
        
        this.markUnsavedChanges(false);
    }
    
    /**
     * Create the dialog content element
     */
    createDialogContent() {
        return $el("div", {
            className: "prompt-companion-dialog-content",
            style: {
                width: "100%",
                height: "100%",
                display: "flex",
                flexDirection: "column",
                backgroundColor: "#2d2d2d",
                color: "#ffffff",
                overflow: "hidden"
            }
        }, [
            // Header
            $el("div", {
                className: "prompt-companion-dialog-header",
                style: {
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "15px 20px",
                    borderBottom: "1px solid #404040",
                    flexShrink: "0"
                }
            }, [
                $el("h3", {
                    textContent: "Edit Subprompts",
                    style: { margin: "0", fontSize: "18px" }
                }),
                $el("button", {
                    className: "prompt-companion-close-btn",
                    textContent: "×",
                    style: {
                        background: "none",
                        border: "none",
                        color: "#ffffff",
                        fontSize: "24px",
                        cursor: "pointer",
                        padding: "0",
                        width: "30px",
                        height: "30px"
                    },
                    onclick: () => this.hide()
                })
            ]),
            
            // Main body with split panels
            $el("div", {
                className: "prompt-companion-dialog-body",
                style: {
                    flex: "1",
                    overflow: "visible",
                    display: "flex",
                    minHeight: "0"
                }
            }, [
                // Left tree panel
                $el("div", {
                    className: "prompt-companion-tree-panel",
                    style: {
                        width: "320px",
                        minWidth: "320px",
                        display: "flex",
                        flexDirection: "column",
                        borderRight: "1px solid #404040"
                    }
                }, [
                    $el("div", {
                        className: "prompt-companion-panel-header",
                        style: {
                            padding: "15px",
                            borderBottom: "1px solid #404040",
                            flexShrink: "0"
                        }
                    }, [
                        $el("h4", {
                            textContent: "Subprompts",
                            style: { margin: "0 0 12px 0", fontSize: "16px" }
                        }),
                        // Compact button grid - all buttons in optimal layout
                        $el("div", {
                            className: "prompt-companion-tree-actions",
                            style: {
                                display: "grid",
                                gridTemplateColumns: "1fr 1fr",
                                gap: "6px",
                                marginBottom: "6px"
                            }
                        }, [
                            $el("button", {
                                className: "prompt-companion-btn prompt-companion-btn-sm",
                                textContent: "New Folder",
                                style: {
                                    padding: "6px 8px",
                                    backgroundColor: "#404040",
                                    border: "none",
                                    borderRadius: "4px",
                                    color: "#ffffff",
                                    cursor: "pointer",
                                    fontSize: "11px",
                                    minHeight: "28px",
                                    whiteSpace: "nowrap",
                                    overflow: "hidden",
                                    textOverflow: "ellipsis"
                                },
                                onclick: () => this.createFolder()
                            }),
                            $el("button", {
                                className: "prompt-companion-btn prompt-companion-btn-sm",
                                textContent: "New Sub",
                                title: "New Subprompt",
                                style: {
                                    padding: "6px 8px",
                                    backgroundColor: "#404040",
                                    border: "none",
                                    borderRadius: "4px",
                                    color: "#ffffff",
                                    cursor: "pointer",
                                    fontSize: "11px",
                                    minHeight: "28px",
                                    whiteSpace: "nowrap",
                                    overflow: "hidden",
                                    textOverflow: "ellipsis"
                                },
                                onclick: () => this.createSubprompt()
                            }),
                            $el("button", {
                                className: "prompt-companion-btn prompt-companion-btn-sm",
                                textContent: "Expand",
                                title: "Expand All Folders",
                                style: {
                                    padding: "6px 8px",
                                    backgroundColor: "#2d3748",
                                    border: "1px solid #4a5568",
                                    borderRadius: "3px",
                                    color: "#ffffff",
                                    cursor: "pointer",
                                    fontSize: "11px",
                                    minHeight: "28px",
                                    whiteSpace: "nowrap",
                                    overflow: "hidden",
                                    textOverflow: "ellipsis"
                                },
                                onclick: () => {
                                    if (this.treeView && this.treeView.expandAll) {
                                        this.treeView.expandAll();
                                    }
                                }
                            }),
                            $el("button", {
                                className: "prompt-companion-btn prompt-companion-btn-sm",
                                textContent: "Collapse",
                                title: "Collapse All Folders",
                                style: {
                                    padding: "6px 8px",
                                    backgroundColor: "#2d3748",
                                    border: "1px solid #4a5568",
                                    borderRadius: "3px",
                                    color: "#ffffff",
                                    cursor: "pointer",
                                    fontSize: "11px",
                                    minHeight: "28px",
                                    whiteSpace: "nowrap",
                                    overflow: "hidden",
                                    textOverflow: "ellipsis"
                                },
                                onclick: () => {
                                    if (this.treeView && this.treeView.collapseAll) {
                                        this.treeView.collapseAll();
                                    }
                                }
                            })
                        ])
                    ]),
                    $el("div", {
                        className: "prompt-companion-search-container",
                        style: {
                            padding: "8px 15px 12px 15px",
                            flexShrink: "0"
                        }
                    }, [
                        $el("input", {
                            type: "text",
                            className: "prompt-companion-input prompt-companion-search",
                            placeholder: "Search subprompts...",
                            style: {
                                width: "100%",
                                padding: "10px 14px",
                                backgroundColor: "#1a1a1a",
                                border: "1px solid #404040",
                                borderRadius: "4px",
                                color: "#ffffff",
                                fontSize: "14px",
                                boxSizing: "border-box"
                            },
                            oninput: (e) => this.searchSubprompts(e.target.value)
                        })
                    ]),
                    $el("div", {
                        id: "prompt-companion-tree-container",
                        className: "prompt-companion-tree-container",
                        style: {
                            flex: "1",
                            overflow: "auto",
                            minHeight: "0"
                        }
                    })
                ]),
                
                // Right edit panel
                $el("div", {
                    className: "prompt-companion-edit-panel",
                    id: "prompt-companion-edit-panel",
                    style: {
                        display: "none",
                        flex: "1",
                        flexDirection: "column",
                        overflow: "auto",
                        minHeight: "0"
                    }
                }, [
                    $el("div", {
                        className: "prompt-companion-panel-header",
                        style: {
                            padding: "18px 20px",
                            borderBottom: "1px solid #404040",
                            flexShrink: "0"
                        }
                    }, [
                        $el("h4", {
                            textContent: "Edit Subprompt",
                            style: { margin: "0", fontSize: "16px" }
                        })
                    ]),
                    $el("div", {
                        className: "prompt-companion-edit-form",
                        id: "prompt-companion-edit-form",
                        style: {
                            flex: "1",
                            overflow: "auto",
                            padding: "20px",
                            minHeight: "0"
                        }
                    }, [
                        this.createEditForm()
                    ])
                ]),
                
                // Placeholder panel when no subprompt is selected
                $el("div", {
                    className: "prompt-companion-placeholder-panel",
                    id: "prompt-companion-placeholder-panel",
                    style: {
                        flex: "1",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center"
                    }
                }, [
                    $el("div", {
                        className: "prompt-companion-placeholder-content",
                        style: {
                            textAlign: "center",
                            padding: "40px 20px"
                        }
                    }, [
                        $el("h4", {
                            textContent: "No Subprompt Selected",
                            style: { margin: "0 0 16px 0", fontSize: "18px", color: "#cccccc" }
                        }),
                        $el("p", {
                            textContent: "Select a subprompt from the tree to edit it, or create a new one.",
                            style: { margin: "0", fontSize: "14px", color: "#999999", lineHeight: "1.4" }
                        })
                    ])
                ])
            ]),
            
            // Footer with action buttons
            $el("div", {
                className: "prompt-companion-dialog-footer",
                style: {
                    display: "flex",
                    justifyContent: "flex-end",
                    gap: "10px",
                    padding: "15px 20px",
                    borderTop: "1px solid #404040",
                    flexShrink: "0",
                    backgroundColor: "#2d2d2d"
                }
            }, [
                $el("button", {
                    className: "prompt-companion-btn prompt-companion-btn-primary",
                    textContent: "OK",
                    style: {
                        padding: "10px 24px",
                        backgroundColor: "#007acc",
                        border: "none",
                        borderRadius: "4px",
                        color: "#ffffff",
                        cursor: "pointer",
                        fontSize: "14px",
                        minHeight: "40px"
                    },
                    onclick: () => this.handleOKButton()
                }),
                $el("button", {
                    className: "prompt-companion-btn",
                    textContent: "Cancel",
                    style: {
                        padding: "10px 24px",
                        backgroundColor: "#6c757d",
                        border: "none",
                        borderRadius: "4px",
                        color: "#ffffff",
                        cursor: "pointer",
                        fontSize: "14px",
                        minHeight: "40px"
                    },
                    onclick: () => this.hide()
                })
            ])
        ]);
    }
    
    /**
     * Hide the dialog with unsaved changes check
     */
    async hide() {
        if (this.unsavedChanges) {
            const shouldClose = await this.showConfirmDialog("You have unsaved changes. Are you sure you want to close?");
            if (!shouldClose) {
                return false;
            }
        }
        
        // Clean up the mutation observer
        if (this.positionObserver) {
            this.positionObserver.disconnect();
            this.positionObserver = null;
        }
        
        // Clear the tree view instance so a fresh one is created on next open
        if (window.PromptCompanion?.clearTreeView) {
            window.PromptCompanion.clearTreeView();
        }
        this.treeView = null;
        
        this.dialog.close();
        return true;
    }
    
    /**
     * Handle OK button - save if edit panel is visible, otherwise just close
     */
    async handleOKButton() {
        const editPanel = this.element.querySelector("#prompt-companion-edit-panel");
        const isEditPanelVisible = editPanel && editPanel.style.display !== "none";
        
        if (isEditPanelVisible && this.currentSubprompt) {
            // Save the current subprompt before closing
            if (await this.saveSubprompt()) {
                this.dialog.close();
            }
        } else {
            // No subprompt selected or edit panel not visible, just close
            this.dialog.close();
        }
    }
    
    /**
     * Load subprompt data into the edit form
     */
    async loadSubpromptForEditing(subprompt) {
        if (!subprompt) return;
        
        this.currentSubprompt = subprompt;
        this.isEditing = true;
        
        // Show the edit panel and hide placeholder
        this.showEditPanel();
        
        // Calculate folder path for display using hierarchical calculation
        let displayFolderPath = "";
        try {
            // If subprompt has folder_id, calculate the hierarchical path
            if (subprompt.folder_id) {
                displayFolderPath = await this.calculateFolderPath(subprompt.folder_id);
            }
            // Fallback to legacy folder_path if no folder_id
            else if (subprompt.folder_path || subprompt.folderPath) {
                displayFolderPath = subprompt.folder_path || subprompt.folderPath || "";
            }
        } catch (error) {
            console.warn("Error calculating folder path:", error);
            // Fallback to legacy folder_path
            displayFolderPath = subprompt.folder_path || subprompt.folderPath || "";
        }
        
        // Update edit panel header with subprompt name and calculated folder path
        this.updateEditPanelHeader(subprompt.name || subprompt.id, displayFolderPath);
        
        // Populate form fields
        this.setFormValue("subprompt-positive", subprompt.positive || "");
        this.setFormValue("subprompt-negative", subprompt.negative || "");
        this.setFormValue("subprompt-triggers", subprompt.trigger_words ? subprompt.trigger_words.join(", ") : "");
        
        // Load nested subprompts - use 'order' field from storage with proper conversion
        const rawOrder = subprompt.order || [];
        const convertedNested = this.convertOrderToNested(rawOrder);
        this.loadNestedSubprompts(convertedNested);
        
        // Update preview asynchronously
        this.updatePreview().catch(console.error);
        this.markUnsavedChanges(false);
    }
    
    /**
     * Clear the edit form
     */
    clearForm() {
        this.currentSubprompt = null;
        this.isEditing = false;
        
        // Hide the edit panel and show placeholder
        this.showPlaceholderPanel();
        
        // Clear edit panel header
        this.updateEditPanelHeader();
        
        this.setFormValue("subprompt-positive", "");
        this.setFormValue("subprompt-negative", "");
        this.setFormValue("subprompt-triggers", "");
        
        this.loadNestedSubprompts([]);
        this.clearValidationMessages();
        // Update preview asynchronously
        this.updatePreview().catch(console.error);
        this.markUnsavedChanges(false);
    }
    
    /**
     * Load nested subprompts list as draggable items
     */
    async loadNestedSubprompts(nestedList = []) {
        const container = this.element.querySelector("#subprompt-nested-list");
        if (!container) return;
        
        // Store available subprompts for the add dialog
        try {
            const response = await api.fetchApi('/prompt_companion/subprompts');
            if (response.ok) {
                this.allSubprompts = await response.json();
            }
        } catch (error) {
            console.error("Error fetching subprompts:", error);
            this.allSubprompts = [];
        }
        
        // Clear existing content
        container.innerHTML = "";
        
        // Ensure [Self] is always included if not already present, but preserve order
        let finalNestedList = [...nestedList];
        if (!finalNestedList.includes("[Self]")) {
            // Add [Self] at the beginning only if not present
            finalNestedList.unshift("[Self]");
        }
        
        // Create draggable items for each nested subprompt in the exact order specified
        finalNestedList.forEach((item, index) => {
            const itemElement = this.createNestedSubpromptItem(item, index);
            container.appendChild(itemElement);
        });
        
        // Update preview after loading nested subprompts
        this.updatePreview().catch(console.error);
    }
    
    /**
     * Create a draggable nested subprompt item
     */
    createNestedSubpromptItem(item, index) {
        // Get better display name for nested subprompts
        const displayName = this.getNestedSubpromptDisplayName(item);
        
        const itemElement = $el("div", {
            className: "prompt-companion-nested-item",
            draggable: true,
            dataset: { subpromptId: item, index: index.toString() },
            style: {
                padding: "8px 12px",
                margin: "2px 0",
                backgroundColor: "#2a2a2a",
                border: "1px solid #404040",
                borderRadius: "4px",
                cursor: "move",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between"
            }
        }, [
            $el("div", {
                className: "prompt-companion-nested-item-content",
                style: { display: "flex", alignItems: "center" }
            }, [
                $el("span", {
                    className: "prompt-companion-drag-handle",
                    textContent: "⋮⋮",
                    style: {
                        marginRight: "8px",
                        color: "#888",
                        fontSize: "14px"
                    }
                }),
                $el("span", {
                    className: "prompt-companion-nested-item-name",
                    textContent: displayName,
                    style: {
                        color: item === "[Self]" ? "#4CAF50" : "#ffffff",
                        fontWeight: item === "[Self]" ? "bold" : "normal"
                    }
                })
            ]),
            // Only show remove button for items that are NOT [Self] - use empty div instead of null
            item === "[Self]" ? $el("div", { style: { width: "24px", height: "18px" } }) : $el("button", {
                type: "button",
                className: "prompt-companion-btn-remove",
                textContent: "×",
                style: {
                    background: "none",
                    border: "none",
                    color: "#dc3545",
                    cursor: "pointer",
                    fontSize: "18px",
                    padding: "0 6px"
                },
                onclick: (e) => {
                    e.stopPropagation();
                    // FIX: Don't use captured index, find current index dynamically
                    this.removeNestedSubpromptItemByElement(itemElement);
                }
            })
        ]);
        
        // Add drag and drop event listeners
        this.setupDragAndDrop(itemElement);
        
        return itemElement;
    }
    
    /**
     * Setup drag and drop functionality for nested subprompt items
     */
    setupDragAndDrop(element) {
        element.addEventListener('dragstart', (e) => {
            this.draggedNestedItem = element;
            e.dataTransfer.effectAllowed = 'move';
            element.style.opacity = '0.5';
        });
        
        element.addEventListener('dragend', (e) => {
            element.style.opacity = '1';
            this.draggedNestedItem = null;
            // Remove drop indicators
            this.element.querySelectorAll('.drop-indicator').forEach(el => el.remove());
        });
        
        element.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'move';
            
            if (this.draggedNestedItem && this.draggedNestedItem !== element) {
                this.showDropIndicator(element, e);
            }
        });
        
        element.addEventListener('drop', (e) => {
            e.preventDefault();
            if (this.draggedNestedItem && this.draggedNestedItem !== element) {
                this.reorderNestedItems(this.draggedNestedItem, element, e);
            }
        });
    }
    
    /**
     * Show drop indicator during drag operation
     */
    showDropIndicator(element, event) {
        // Remove existing indicators
        this.element.querySelectorAll('.drop-indicator').forEach(el => el.remove());
        
        const rect = element.getBoundingClientRect();
        const midY = rect.top + rect.height / 2;
        const isAfter = event.clientY > midY;
        
        const indicator = $el("div", {
            className: "drop-indicator",
            style: {
                height: "2px",
                backgroundColor: "#007acc",
                margin: "2px 0",
                borderRadius: "1px"
            }
        });
        
        if (isAfter) {
            element.parentNode.insertBefore(indicator, element.nextSibling);
        } else {
            element.parentNode.insertBefore(indicator, element);
        }
    }
    
    /**
     * Reorder nested items after drag and drop
     */
    reorderNestedItems(draggedElement, targetElement, event) {
        const container = this.element.querySelector("#subprompt-nested-list");
        const rect = targetElement.getBoundingClientRect();
        const midY = rect.top + rect.height / 2;
        const isAfter = event.clientY > midY;
        
        // Remove drop indicators
        this.element.querySelectorAll('.drop-indicator').forEach(el => el.remove());
        
        // Reorder DOM elements
        if (isAfter) {
            container.insertBefore(draggedElement, targetElement.nextSibling);
        } else {
            container.insertBefore(draggedElement, targetElement);
        }
        
        // Update indices and mark as changed
        this.updateNestedItemIndices();
        this.markUnsavedChanges(true);
        
        // Update preview after reordering
        this.schedulePreviewUpdate('reorder');
    }
    
    /**
     * Update the index data attributes after reordering
     */
    updateNestedItemIndices() {
        const items = this.element.querySelectorAll("#subprompt-nested-list .prompt-companion-nested-item");
        items.forEach((item, index) => {
            item.dataset.index = index.toString();
        });
    }
    
    /**
     * Get display name for nested subprompt items
     */
    getNestedSubpromptDisplayName(item) {
        if (item === "[Self]") {
            return "[Self]";
        }
        
        // If it's already a display name (contains ": "), return as is
        if (typeof item === 'string' && item.includes(': ')) {
            return item;
        }
        
        // If it's a UUID, try to find the corresponding subprompt
        if (this.allSubprompts && Array.isArray(this.allSubprompts)) {
            const subprompt = this.allSubprompts.find(sp => sp.id === item);
            if (subprompt) {
                // Use the same format as combo boxes: "folder_path: name" or just "name" for root
                return subprompt.folder_path ?
                    `${subprompt.folder_path}: ${subprompt.name}` :
                    subprompt.name;
            }
        }
        
        // Return the original item if we can't find a better display name
        return item;
    }
    
    /**
     * Remove a nested subprompt item by finding its current index dynamically
     * This fixes the issue where drag-and-drop changes indices but onclick handlers use stale indices
     */
    removeNestedSubpromptItemByElement(itemElement) {
        const container = this.element.querySelector("#subprompt-nested-list");
        if (!itemElement || !container.contains(itemElement)) {
            console.warn("Item element not found or not in container");
            return;
        }
        
        // Prevent removal of [Self] marker
        const subpromptId = itemElement.dataset.subpromptId;
        if (subpromptId === "[Self]") {
            console.warn("Cannot remove [Self] marker from nested subprompts");
            return;
        }
        
        // Remove the element
        itemElement.remove();
        this.updateNestedItemIndices();
        this.markUnsavedChanges(true);
        
        // Update preview after removing item
        this.schedulePreviewUpdate('remove');
        
        // Show empty state if no items left (but always keep [Self])
        if (container.children.length === 0) {
            this.loadNestedSubprompts([]);
        }
    }
    
    /**
     * Remove a nested subprompt item (legacy method for backward compatibility)
     */
    removeNestedSubpromptItem(index) {
        const container = this.element.querySelector("#subprompt-nested-list");
        const item = container.querySelector(`[data-index="${index}"]`);
        if (item) {
            this.removeNestedSubpromptItemByElement(item);
        }
    }
    
    /**
     * Show dialog to add nested subprompts
     */
    async showAddSubpromptDialog() {
        if (!this.allSubprompts) return;
        
        // Build available subprompts from the list with folder paths using consistent format
        let availableSubprompts = [];
        this.allSubprompts.forEach(subprompt => {
            // Use the same format as combo boxes: "folder_path: name" or just "name" for root
            const displayName = subprompt.folder_path ?
                `${subprompt.folder_path}: ${subprompt.name}` :
                subprompt.name;
            availableSubprompts.push(displayName);
        });
        availableSubprompts.sort();
        
        const currentNested = this.getCurrentNestedSubprompts();
        
        // Filter out the current subprompt to prevent circular reference
        if (this.currentSubprompt && this.currentSubprompt.name) {
            const currentDisplayName = this.currentSubprompt.folder_path ?
                `${this.currentSubprompt.folder_path}: ${this.currentSubprompt.name}` :
                this.currentSubprompt.name;
            availableSubprompts = availableSubprompts.filter(name => name !== currentDisplayName);
        }
        
        // Add [Self] as first option if not already present
        const options = ["[Self]", ...availableSubprompts];
        const filteredOptions = options.filter(id => !currentNested.includes(id));
        
        if (filteredOptions.length === 0) {
            await this.showAlertDialog("All available subprompts are already added.");
            return;
        }
        
        // Create selection dialog
        const dialogContent = $el("div", {
            style: {
                minWidth: "300px",
                padding: "20px"
            }
        }, [
            $el("h4", {
                textContent: "Add Nested Subprompt",
                style: { marginTop: "0", marginBottom: "15px" }
            }),
            $el("select", {
                id: "add-subprompt-selector",
                size: Math.min(8, filteredOptions.length),
                style: {
                    width: "100%",
                    minHeight: "120px",
                    marginBottom: "15px"
                }
            }, filteredOptions.map(id => $el("option", {
                value: id,
                textContent: id
            }))),
            $el("div", {
                style: { textAlign: "right" }
            }, [
                $el("button", {
                    textContent: "Add",
                    style: {
                        marginRight: "10px",
                        padding: "6px 12px",
                        backgroundColor: "#007acc",
                        color: "white",
                        border: "none",
                        borderRadius: "4px",
                        cursor: "pointer"
                    },
                    onclick: () => {
                        const selector = document.getElementById("add-subprompt-selector");
                        const selectedOption = selector.options[selector.selectedIndex];
                        if (selectedOption) {
                            this.addNestedSubprompt(selectedOption.value);
                            document.body.removeChild(overlay);
                        }
                    }
                }),
                $el("button", {
                    textContent: "Cancel",
                    style: {
                        padding: "6px 12px",
                        backgroundColor: "#6c757d",
                        color: "white",
                        border: "none",
                        borderRadius: "4px",
                        cursor: "pointer"
                    },
                    onclick: () => document.body.removeChild(overlay)
                })
            ])
        ]);
        
        const overlay = $el("div", {
            style: {
                position: "fixed",
                top: "0",
                left: "0",
                width: "100%",
                height: "100%",
                backgroundColor: "rgba(0,0,0,0.5)",
                zIndex: "10003",
                display: "flex",
                alignItems: "center",
                justifyContent: "center"
            }
        }, [
            $el("div", {
                style: {
                    backgroundColor: "#2d2d2d",
                    border: "1px solid #404040",
                    borderRadius: "8px",
                    color: "#ffffff"
                }
            }, [dialogContent])
        ]);
        
        document.body.appendChild(overlay);
    }
    
    /**
     * Get current nested subprompts from the UI
     */
    getCurrentNestedSubprompts() {
        const items = this.element.querySelectorAll("#subprompt-nested-list .prompt-companion-nested-item");
        const result = Array.from(items).map(item => item.dataset.subpromptId);
        return result;
    }
    
    /**
     * Add a nested subprompt
     */
    addNestedSubprompt(subpromptId) {
        const container = this.element.querySelector("#subprompt-nested-list");
        const currentNested = this.getCurrentNestedSubprompts();
        
        // Clear empty state if present
        if (container.querySelector(".prompt-companion-nested-empty")) {
            container.innerHTML = "";
        }
        
        // Add the new item
        const index = currentNested.length;
        const itemElement = this.createNestedSubpromptItem(subpromptId, index);
        container.appendChild(itemElement);
        
        this.updateNestedItemIndices();
        this.markUnsavedChanges(true);
        
        // Update preview after adding item
        this.schedulePreviewUpdate('add');
    }
    
    /**
     * Convert storage 'order' format to frontend 'nested_subprompts' format
     * Backend uses 'attached' for [Self], frontend uses '[Self]'
     * This method ensures proper ordering and handles different stored formats
     */
    convertOrderToNested(order) {
        if (!Array.isArray(order)) {
            return ["[Self]"];
        }
        
        const result = [];
        
        // Process each item in order to maintain the exact sequence
        for (const item of order) {
            if (item === "attached") {
                result.push("[Self]");
            } else if (item && typeof item === 'string' && item.trim()) {
                // Handle different formats: UUIDs, names, or "folder_path: name"
                result.push(item.trim());
            }
        }
        
        // Ensure [Self] is always included if not already present
        if (!result.includes("[Self]")) {
            result.unshift("[Self]");
        }
        
        return result;
    }
    
    /**
     * Convert frontend 'nested_subprompts' format to storage 'order' format
     * Frontend uses '[Self]' for current subprompt, backend uses 'attached'
     */
    convertNestedToOrder(nested) {
        if (!Array.isArray(nested)) {
            return ["attached"];
        }
        
        return nested.map(item => {
            if (item === "[Self]") {
                return "attached";
            } else {
                return item;
            }
        });
    }
    
    /**
     * Set form field value
     */
    setFormValue(id, value) {
        const element = this.element.querySelector(`#${id}`);
        if (element) {
            element.value = value;
        }
    }
    
    /**
     * Get form field value
     */
    getFormValue(id) {
        const element = this.element.querySelector(`#${id}`);
        return element ? element.value : "";
    }
    
    /**
     * Validate form content
     */
    validateContent() {
        const positive = this.getFormValue("subprompt-positive");
        
        const messages = [];
        
        // Content validation
        if (!positive.trim() && !this.getFormValue("subprompt-negative").trim()) {
            messages.push({ type: "warning", message: "At least one of positive or negative prompt should be specified" });
        }
        
        this.displayValidationMessages(messages);
        return messages.filter(m => m.type === "error").length === 0;
    }
    
    /**
     * Display validation messages
     */
    displayValidationMessages(messages) {
        const container = this.element.querySelector("#validation-messages");
        if (!container) return;
        
        container.innerHTML = "";
        
        messages.forEach(({ type, message }) => {
            const div = $el("div", {
                className: `validation-${type}`,
                textContent: message
            });
            container.appendChild(div);
        });
    }
    
    /**
     * Clear validation messages
     */
    clearValidationMessages() {
        const container = this.element.querySelector("#validation-messages");
        if (container) {
            container.innerHTML = "";
        }
    }
    
    /**
     * Debounced validation
     */
    debounceValidation() {
        if (this.validationTimer) {
            clearTimeout(this.validationTimer);
        }
        this.validationTimer = setTimeout(() => this.validateContent(), 300);
    }
    
    /**
     * Debounced preview update for real-time typing
     */
    debouncePreviewUpdate() {
        if (this.previewUpdateTimer) {
            clearTimeout(this.previewUpdateTimer);
        }
        this.previewUpdateTimer = setTimeout(() => {
            this.updatePreview().catch(console.error);
        }, 150); // Shorter delay for more responsive preview updates
    }
    
    /**
     * Update preview display with resolved nested subprompts
     */
    async updatePreview() {
        const preview = this.element.querySelector("#subprompt-preview");
        if (!preview) {
            return;
        }
        
        // Get the resolved content (combined with nested subprompts)
        const resolvedContent = await this.resolveNestedSubprompts();
        
        let previewHtml = "";
        if (resolvedContent.positive.trim()) {
            previewHtml += `<div class="preview-positive"><strong>Positive:</strong> ${this.escapeHtml(resolvedContent.positive)}</div>`;
        }
        if (resolvedContent.negative.trim()) {
            previewHtml += `<div class="preview-negative"><strong>Negative:</strong> ${this.escapeHtml(resolvedContent.negative)}</div>`;
        }
        
        if (!previewHtml) {
            previewHtml = '<div class="preview-empty">No content to preview</div>';
        }
        
        
        preview.innerHTML = previewHtml;
        
    }
    
    /**
     * Schedule a preview update with robust DOM timing handling
     * This ensures DOM changes are fully processed before reading current state
     */
    schedulePreviewUpdate(source = 'unknown') {
        const preview = this.element.querySelector("#subprompt-preview");
        if (!preview) return;
        
        
        
        // Cancel any pending preview update
        if (this.pendingPreviewUpdate) {
            cancelAnimationFrame(this.pendingPreviewUpdate);
            this.pendingPreviewUpdate = null;
        }
        
        // Add visual indicator that preview is updating
        const originalContent = preview.innerHTML;
        preview.innerHTML = '<div class="preview-updating" style="color: #888; font-style: italic;">Updating preview...</div>';
        
        
        // Capture method references before entering async context to avoid 'this' binding issues
        const escapeHtml = this.escapeHtml.bind(this);
        const getCurrentNestedSubprompts = this.getCurrentNestedSubprompts.bind(this);
        const resolveNestedSubpromptsWithOrder = this.resolveNestedSubpromptsWithOrder.bind(this);
        
        // Use triple requestAnimationFrame + forced reflow for maximum DOM settling
        this.pendingPreviewUpdate = requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                requestAnimationFrame(async () => {
                    try {
                        
                        
                        // Force multiple reflows to ensure DOM is fully processed
                        const container = this.element.querySelector("#subprompt-nested-list");
                        if (container) {
                            container.offsetHeight; // Force reflow
                            container.scrollTop; // Force additional layout calculation
                            
                        }
                        
                        // Small delay to ensure all DOM operations are complete
                        await new Promise(resolve => setTimeout(resolve, 10));
                        
                        
                        // Get fresh DOM state for nested subprompts using bound method
                        const currentNested = getCurrentNestedSubprompts();
                        
                        // Get resolved content using fresh DOM state - pass currentNested directly
                        const resolvedContent = await resolveNestedSubpromptsWithOrder(currentNested);
                        
                        let previewHtml = "";
                        if (resolvedContent.positive.trim()) {
                            previewHtml += `<div class="preview-positive"><strong>Positive:</strong> ${escapeHtml(resolvedContent.positive)}</div>`;
                        }
                        if (resolvedContent.negative.trim()) {
                            previewHtml += `<div class="preview-negative"><strong>Negative:</strong> ${escapeHtml(resolvedContent.negative)}</div>`;
                        }
                        
                        if (!previewHtml) {
                            previewHtml = '<div class="preview-empty">No content to preview</div>';
                        }
                        
                        
                        
                        preview.innerHTML = previewHtml;
                        
                        
                        // Add subtle flash effect to show update happened
                        preview.style.transition = 'background-color 0.2s ease';
                        preview.style.backgroundColor = '#2a4d3a';
                        setTimeout(() => {
                            preview.style.backgroundColor = '';
                            setTimeout(() => {
                                preview.style.transition = '';
                            }, 200);
                        }, 100);
                        
                        this.pendingPreviewUpdate = null;
                        
                        
                    } catch (error) {
                        console.error(`Error in preview update (${source}):`, error);
                        
                        preview.innerHTML = originalContent;
                        this.pendingPreviewUpdate = null;
                    }
                });
            });
        });
    }
    
    /**
     * Resolve nested subprompts using a specific order from the DOM
     */
    async resolveNestedSubpromptsWithOrder(currentNested) {
        
        
        const currentPositive = this.getFormValue("subprompt-positive").trim();
        const currentNegative = this.getFormValue("subprompt-negative").trim();
        
        
        
        // Convert frontend format to backend format for resolution
        const orderForResolution = this.convertNestedToOrder(currentNested);
        
        
        // Use recursive resolution with circular reference protection
        
        const resolved = this.resolveSubpromptRecursively({
            positive: currentPositive,
            negative: currentNegative,
            order: orderForResolution
        }, new Set());
        
        
        // Remove duplicate terms from the final resolved content
        const finalResult = {
            positive: this.removeDuplicateTerms(resolved.positive),
            negative: this.removeDuplicateTerms(resolved.negative)
        };
        
        
        return finalResult;
    }
    
    /**
     * Force preview update with immediate DOM state reading and visual feedback
     * Used after DOM manipulation operations to ensure preview reflects current state
     * @deprecated Use schedulePreviewUpdate() for better timing handling
     */
    forcePreviewUpdate() {
        this.schedulePreviewUpdate('force');
    }
    
    /**
     * Resolve nested subprompts recursively and return combined content
     */
    async resolveNestedSubprompts() {
        
        
        const currentPositive = this.getFormValue("subprompt-positive").trim();
        const currentNegative = this.getFormValue("subprompt-negative").trim();
        const nestedSubprompts = this.getCurrentNestedSubprompts();
        
        
        
        // Convert frontend format to backend format for resolution
        const orderForResolution = this.convertNestedToOrder(nestedSubprompts);
        
        
        // Use recursive resolution with circular reference protection
        
        const resolved = this.resolveSubpromptRecursively({
            positive: currentPositive,
            negative: currentNegative,
            order: orderForResolution
        }, new Set());
        
        
        // Remove duplicate terms from the final resolved content
        const finalResult = {
            positive: this.removeDuplicateTerms(resolved.positive),
            negative: this.removeDuplicateTerms(resolved.negative)
        };
        
        
        return finalResult;
    }
    
    /**
     * Remove duplicate terms from a comma-separated string, preserving order
     */
    removeDuplicateTerms(text) {
        if (!text || !text.trim()) return text;
        
        // Split by comma, trim whitespace, and filter out empty terms
        const terms = text.split(',').map(term => term.trim()).filter(term => term.length > 0);
        
        // Use Set to track seen terms (case-insensitive) and array to preserve order
        const seen = new Set();
        const uniqueTerms = [];
        
        for (const term of terms) {
            const lowerTerm = term.toLowerCase();
            if (!seen.has(lowerTerm)) {
                seen.add(lowerTerm);
                uniqueTerms.push(term); // Keep original case
            }
        }
        
        return uniqueTerms.join(', ');
    }
    
    /**
     * Recursively resolve a subprompt and all its nested subprompts
     */
    resolveSubpromptRecursively(subprompt, visited = new Set()) {
        
        
        // Start with EMPTY content instead of pre-adding textbox content
        let resolvedPositive = '';
        let resolvedNegative = '';
        
        
        
        // Process nested subprompts in order - use 'order' field from storage
        const orderList = subprompt.order || [];
        
        
        for (let i = 0; i < orderList.length; i++) {
            const nestedId = orderList[i];
            
            
            if (nestedId === "attached") {
                // Add textbox content at this specific position in the order
                if (subprompt.positive && subprompt.positive.trim()) {
                    if (resolvedPositive) {
                        resolvedPositive += ", " + subprompt.positive.trim();
                    } else {
                        resolvedPositive = subprompt.positive.trim();
                    }
                    
                }
                
                if (subprompt.negative && subprompt.negative.trim()) {
                    if (resolvedNegative) {
                        resolvedNegative += ", " + subprompt.negative.trim();
                    } else {
                        resolvedNegative = subprompt.negative.trim();
                    }
                    
                }
                
                continue; // Continue to next item in order
            }
            
            // Prevent circular references
            if (visited.has(nestedId)) {
                console.warn(`Circular reference detected: ${nestedId}`);
                continue;
            }
            
            // Get nested subprompt content - search through the list
            let nestedSubprompt = null;
            
            
            if (this.allSubprompts && Array.isArray(this.allSubprompts)) {
                // Parse the nestedId to handle both new format "folder_path: name" and old formats
                if (nestedId.includes(': ')) {
                    // New format: "folder_path: name"
                    const parts = nestedId.split(': ');
                    const folderPath = parts[0];
                    const name = parts[1];
                    
                    nestedSubprompt = this.allSubprompts.find(sp =>
                        sp.name === name && sp.folder_path === folderPath);
                } else if (nestedId.includes('/')) {
                    // Legacy format: "folder_path/name"
                    const parts = nestedId.split('/');
                    const name = parts[parts.length - 1];
                    const folderPath = parts.slice(0, -1).join('/');
                    
                    nestedSubprompt = this.allSubprompts.find(sp =>
                        sp.name === name && sp.folder_path === folderPath);
                } else {
                    // Simple name format (root-level subprompts)
                    
                    nestedSubprompt = this.allSubprompts.find(sp =>
                        sp.name === nestedId && (!sp.folder_path || sp.folder_path === ''));
                }
            }
            
            if (nestedSubprompt) {
                
                
                // Create new visited set for this branch
                const branchVisited = new Set(visited);
                branchVisited.add(nestedId);
                
                // Recursively resolve the nested subprompt
                
                const resolvedNested = this.resolveSubpromptRecursively(nestedSubprompt, branchVisited);
                
                
                // Add resolved positive content AT THIS POSITION in the order
                if (resolvedNested.positive && resolvedNested.positive.trim()) {
                    if (resolvedPositive) {
                        resolvedPositive += ", " + resolvedNested.positive.trim();
                    } else {
                        resolvedPositive = resolvedNested.positive.trim();
                    }
                    
                }
                
                // Add resolved negative content AT THIS POSITION in the order
                if (resolvedNested.negative && resolvedNested.negative.trim()) {
                    if (resolvedNegative) {
                        resolvedNegative += ", " + resolvedNested.negative.trim();
                    } else {
                        resolvedNegative = resolvedNested.negative.trim();
                    }
                    
                }
            } else {
                console.warn(`Nested subprompt not found for ID: "${nestedId}" at position ${i}`);
            }
        }
        
        
        
        const finalResult = {
            positive: resolvedPositive,
            negative: resolvedNegative
        };
        
        
        return finalResult;
    }
    
    /**
     * Escape HTML for safe display
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    /**
     * Save subprompt data
     */
    async saveSubprompt() {
        if (!this.validateContent()) {
            return false;
        }
        
        // Get nested subprompts from the draggable list (in order)
        const nestedSubprompts = this.getCurrentNestedSubprompts();
        
        // Convert frontend format to backend 'order' format
        const orderForStorage = this.convertNestedToOrder(nestedSubprompts);
        
        const subpromptData = {
            name: this.currentSubprompt ? this.currentSubprompt.name : "New Subprompt",
            positive: this.getFormValue("subprompt-positive").trim(),
            negative: this.getFormValue("subprompt-negative").trim(),
            trigger_words: this.getFormValue("subprompt-triggers").split(",").map(w => w.trim()).filter(w => w),
            order: orderForStorage,
            // Use folder_id for UUID-based system, keep folder_path for backward compatibility
            folder_id: this.currentSubprompt ? (this.currentSubprompt.folder_id || null) : null,
            folder_path: this.currentSubprompt ? (this.currentSubprompt.folder_path || this.currentSubprompt.folderPath || null) : null
        };
        
        try {
            const url = this.isEditing && this.currentSubprompt
                ? `/prompt_companion/subprompts/${encodeURIComponent(this.currentSubprompt.id)}`
                : "/prompt_companion/subprompts";
            
            const method = this.isEditing && this.currentSubprompt ? "PUT" : "POST";
            
            // For editing, include the ID in the data
            if (this.isEditing && this.currentSubprompt) {
                subpromptData.id = this.currentSubprompt.id;
            }
            
            const response = await api.fetchApi(url, {
                method: method,
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(subpromptData)
            });
            
            if (response.ok) {
                this.markUnsavedChanges(false);
                
                // Refresh tree view while preserving expanded folder state
                if (this.treeView && this.treeView.refreshTreePreservingState) {
                    await this.treeView.refreshTreePreservingState();
                }
                
                // Update node dropdowns in workflow
                this.updateNodeDropdowns();
                
                this.showMessage("Subprompt saved successfully", "success");
                return true;
            } else {
                const errorData = await response.json();
                this.showMessage(`Save failed: ${errorData.error || "Unknown error"}`, "error");
                return false;
            }
        } catch (error) {
            console.error("Save error:", error);
            this.showMessage(`Save failed: ${error.message}`, "error");
            return false;
        }
    }
    
    /**
     * Revert changes to last saved state
     */
    revertChanges() {
        if (this.currentSubprompt) {
            this.loadSubpromptForEditing(this.currentSubprompt);
        } else {
            this.clearForm();
        }
    }
    
    /**
     * Create new folder
     */
    async createFolder() {
        const name = await this.showInputDialog("Enter folder name:", "");
        if (name && name.trim()) {
            const folderName = name.trim();
            
            if (this.treeView && this.treeView.createFolder) {
                try {
                    const success = await this.treeView.createFolder(folderName);
                    if (success) {
                        // Tree view already refreshes itself with preserved state in createFolder()
                        this.showMessage(`Folder "${folderName}" created successfully`, "success");
                    } else {
                        this.showMessage(`Failed to create folder "${folderName}"`, "error");
                    }
                } catch (error) {
                    console.error("Error creating folder:", error);
                    this.showMessage(`Error creating folder: ${error.message}`, "error");
                }
            } else {
                this.showMessage("Tree view not available", "error");
            }
        }
    }
    
    /**
     * Create new subprompt
     */
    async createSubprompt() {
        // Prompt for subprompt name
        const name = await this.showInputDialog("Enter subprompt name:", "");
        if (!name || !name.trim()) {
            return; // User cancelled or entered empty name
        }
        
        const subpromptName = name.trim();
        
        // Create subprompt on server first
        try {
            const newSubpromptData = {
                name: subpromptName,
                folder_id: null, // Default to root level (null for root)
                folder_path: "", // Keep for backward compatibility
                positive: '',
                negative: '',
                trigger_words: [],
                order: ["attached"] // Use backend format for storage
            };
            
            const response = await api.fetchApi('/prompt_companion/subprompts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(newSubpromptData)
            });
            
            if (response.ok) {
                const savedSubprompt = await response.json();
                
                // Use the tree view's built-in method to refresh while preserving state
                if (this.treeView && this.treeView.refreshTreePreservingState) {
                    await this.treeView.refreshTreePreservingState();
                }

                // Note: No need to call expandParentFolders since refreshTreePreservingState
                // already preserves the correct expanded state from createSubprompt()
                
                // Load the saved subprompt for editing
                this.loadSubpromptForEditing(savedSubprompt);
                this.markUnsavedChanges(false); // It's saved, no unsaved changes yet
                
                // Focus the first field for immediate editing
                const firstField = this.element.querySelector("#subprompt-positive");
                if (firstField) {
                    firstField.focus();
                }
                
                this.showMessage(`Subprompt "${subpromptName}" created successfully`, "success");
            } else {
                const errorData = await response.json();
                this.showMessage(`Failed to create subprompt: ${errorData.error || 'Unknown error'}`, "error");
            }
        } catch (error) {
            console.error("Error creating subprompt:", error);
            this.showMessage(`Error creating subprompt: ${error.message}`, "error");
        }
    }
    
    /**
     * Search subprompts in tree view
     */
    searchSubprompts(term) {
        if (this.treeView && this.treeView.searchTree) {
            this.treeView.searchTree(term);
        }
    }
    
    /**
     * Mark unsaved changes state
     */
    markUnsavedChanges(hasChanges) {
        this.unsavedChanges = hasChanges;
        const header = this.element.querySelector(".prompt-companion-dialog-header h3");
        if (header) {
            header.textContent = hasChanges ? "Edit Subprompts *" : "Edit Subprompts";
            header.style.color = hasChanges ? "#ffc107" : "";
        }
    }
    
    /**
     * Show the edit panel and hide placeholder
     */
    showEditPanel() {
        const editPanel = this.element.querySelector("#prompt-companion-edit-panel");
        const placeholderPanel = this.element.querySelector("#prompt-companion-placeholder-panel");
        
        if (editPanel) editPanel.style.display = "block";
        if (placeholderPanel) placeholderPanel.style.display = "none";
    }
    
    /**
     * Show the placeholder panel and hide edit panel
     */
    showPlaceholderPanel() {
        const editPanel = this.element.querySelector("#prompt-companion-edit-panel");
        const placeholderPanel = this.element.querySelector("#prompt-companion-placeholder-panel");
        
        if (editPanel) editPanel.style.display = "none";
        if (placeholderPanel) placeholderPanel.style.display = "block";
    }
    
    /**
     * Update the edit panel header with subprompt name and folder path
     */
    updateEditPanelHeader(subpromptName, folderPath) {
        const header = this.element.querySelector("#prompt-companion-edit-panel .prompt-companion-panel-header h4");
        if (header) {
            if (subpromptName) {
                let headerText = "Edit Subprompt: ";
                if (folderPath && folderPath.trim()) {
                    // Convert forward slashes to backslashes for Windows-style display
                    const displayPath = folderPath.replace(/\//g, '\\');
                    headerText += `${displayPath}\\${subpromptName}`;
                } else {
                    headerText += subpromptName;
                }
                header.textContent = headerText;
            } else {
                header.textContent = "Edit Subprompt";
            }
        }
    }
    
    /**
     * Calculate hierarchical folder path from folder_id
     */
    async calculateFolderPath(folderId) {
        if (!folderId) return "";
        
        try {
            // Get all folders to build the hierarchy
            const foldersResponse = await api.fetchApi('/prompt_companion/folders');
            if (!foldersResponse.ok) {
                console.warn("Failed to fetch folders for path calculation");
                return "";
            }
            
            const folders = await foldersResponse.json();
            if (!Array.isArray(folders) || folders.length === 0) {
                return "";
            }
            
            // Create folder lookup map
            const folderMap = {};
            folders.forEach(folder => {
                folderMap[folder.id] = folder;
            });
            
            // Calculate path by walking up the parent chain
            const pathParts = [];
            let currentFolder = folderMap[folderId];
            
            // Prevent infinite loops with a max depth
            let depth = 0;
            const maxDepth = 20;
            
            while (currentFolder && depth < maxDepth) {
                pathParts.unshift(currentFolder.name);
                currentFolder = currentFolder.parent_id ? folderMap[currentFolder.parent_id] : null;
                depth++;
            }
            
            return pathParts.join('/'); // Use forward slashes internally, convert to backslashes in display
            
        } catch (error) {
            console.error("Error calculating folder path:", error);
            return "";
        }
    }
    
    /**
     * Update node dropdowns in the workflow
     */
    updateNodeDropdowns() {
        const promptCompanionNodes = [
            "PromptCompanion_AddSubprompt",
            "PromptCompanion_SubpromptToStrings",
            "PromptCompanion_StringsToSubprompt",
            "PromptCompanion_LoadCheckpointWithSubprompt"
        ];
        
        if (app.graph && app.graph._nodes) {
            app.graph._nodes.forEach(node => {
                if (node.type && promptCompanionNodes.includes(node.type)) {
                    if (node.widgets) {
                        node.widgets.forEach(widget => {
                            if (widget.name && widget.name.includes("subprompt") && widget.options) {
                                this.refreshWidgetOptions(widget);
                            }
                        });
                    }
                }
            });
        }
    }
    
    /**
     * Refresh widget options
     */
    async refreshWidgetOptions(widget) {
        try {
            const response = await api.fetchApi("/prompt_companion/subprompts/dropdown_options");
            if (response.ok) {
                const dropdownOptions = await response.json();
                // Only update if we got valid options
                if (dropdownOptions && dropdownOptions.length > 0 &&
                    !dropdownOptions.includes("[Error Loading Subprompts]")) {
                    widget.options.values = dropdownOptions;
                }
            }
        } catch (error) {
            console.error("Failed to refresh widget options:", error);
            // Don't clear options on error - leave them unchanged
        }
    }
    
    /**
     * Show temporary message
     */
    showMessage(text, type = "info") {
        const messageEl = $el("div", {
            className: `prompt-companion-message prompt-companion-message-${type}`,
            textContent: text,
            style: {
                position: "fixed",
                top: "20px",
                right: "20px",
                padding: "10px 20px",
                borderRadius: "4px",
                zIndex: "10000",
                backgroundColor: type === "success" ? "#28a745" : 
                              type === "error" ? "#dc3545" : "#17a2b8",
                color: "white"
            }
        });
        
        document.body.appendChild(messageEl);
        
        setTimeout(() => {
            if (messageEl.parentNode) {
                messageEl.parentNode.removeChild(messageEl);
            }
        }, 3000);
    }
    
    /**
     * Handle window resize
     */
    handleResize() {
        const content = this.element.querySelector(".prompt-companion-dialog-content");
        if (content) {
            const maxHeight = window.innerHeight * 0.9;
            const maxWidth = window.innerWidth * 0.9;
            
            content.style.maxHeight = `${maxHeight}px`;
            content.style.maxWidth = `${maxWidth}px`;
            
            // Ensure dialog stays properly centered
            this.centerDialog();
        }
    }
    
    /**
     * Setup resize handling
     */
    setupResizeHandling() {
        this.resizing = false;
        this.startX = 0;
        this.startY = 0;
        this.startWidth = 0;
        this.startHeight = 0;
    }
    
    /**
     * Start resize operation
     */
    startResize(e) {
        e.preventDefault();
        e.stopPropagation();
        
        this.resizing = true;
        this.startX = e.clientX;
        this.startY = e.clientY;
        
        const content = this.element.querySelector(".prompt-companion-dialog-content");
        if (content) {
            const rect = content.getBoundingClientRect();
            this.startWidth = rect.width;
            this.startHeight = rect.height;
        }
        
        // Add global mouse event listeners
        this.resizeHandler = (e) => this.doResize(e);
        this.stopResizeHandler = () => this.stopResize();
        
        document.addEventListener('mousemove', this.resizeHandler, { passive: false });
        document.addEventListener('mouseup', this.stopResizeHandler, { once: true });
        
        // Prevent text selection during resize
        document.body.style.userSelect = 'none';
        document.body.style.cursor = 'nw-resize';
    }
    
    /**
     * Perform resize operation
     */
    doResize(e) {
        if (!this.resizing) return;
        
        e.preventDefault();
        
        const deltaX = e.clientX - this.startX;
        const deltaY = e.clientY - this.startY;
        
        const newWidth = Math.max(600, this.startWidth + deltaX);
        const newHeight = Math.max(400, this.startHeight + deltaY);
        
        const content = this.element.querySelector(".prompt-companion-dialog-content");
        if (content) {
            content.style.width = newWidth + 'px';
            content.style.height = newHeight + 'px';
            content.style.maxWidth = 'none';
            content.style.maxHeight = 'none';
        }
    }
    
    /**
     * Stop resize operation
     */
    stopResize() {
        this.resizing = false;
        
        // Remove global event listeners
        if (this.resizeHandler) {
            document.removeEventListener('mousemove', this.resizeHandler);
        }
        
        // Restore text selection and cursor
        document.body.style.userSelect = '';
        document.body.style.cursor = '';
    }
    
    /**
     * Show input dialog using ComfyUI's native API
     */
    async showInputDialog(message, defaultValue = "") {
        // Try ComfyUI's native prompt dialog first
        if (typeof app !== 'undefined' && app.extensionManager && app.extensionManager.dialog && app.extensionManager.dialog.prompt) {
            try {
                return await app.extensionManager.dialog.prompt({
                    title: "Input",
                    message: message,
                    defaultValue: defaultValue || ""
                });
            } catch (error) {
                console.warn("ComfyUI extensionManager dialog.prompt failed, falling back to browser prompt:", error);
            }
        }
        
        // Fallback to browser prompt
        const result = prompt(message, defaultValue || "");
        return result;
    }
    
    /**
     * Show unsaved changes dialog with three options: Save, Discard, Cancel
     * @returns {Promise<string>} 'save', 'discard', or 'cancel'
     */
    async showUnsavedChangesDialog() {
        return new Promise((resolve) => {
            const dialog = $el("div", {
                className: "prompt-companion-unsaved-changes-dialog",
                style: {
                    position: "fixed",
                    top: "50%",
                    left: "50%",
                    transform: "translate(-50%, -50%)",
                    backgroundColor: "#2d2d2d",
                    border: "1px solid #404040",
                    borderRadius: "8px",
                    padding: "20px",
                    zIndex: "10003",
                    minWidth: "400px",
                    maxWidth: "500px",
                    boxShadow: "0 4px 12px rgba(0,0,0,0.5)"
                }
            }, [
                $el("h3", {
                    textContent: "Unsaved Changes",
                    style: {
                        color: "#ffffff",
                        marginTop: "0",
                        marginBottom: "15px",
                        fontSize: "18px"
                    }
                }),
                $el("p", {
                    textContent: "You have unsaved changes to the current subprompt. What would you like to do?",
                    style: {
                        color: "#cccccc",
                        marginBottom: "25px",
                        lineHeight: "1.4"
                    }
                }),
                $el("div", {
                    className: "prompt-companion-dialog-buttons",
                    style: {
                        display: "flex",
                        gap: "12px",
                        justifyContent: "center",
                        flexWrap: "wrap"
                    }
                }, [
                    $el("button", {
                        textContent: "Save Changes",
                        style: {
                            padding: "10px 20px",
                            backgroundColor: "#28a745",
                            color: "white",
                            border: "none",
                            borderRadius: "4px",
                            cursor: "pointer",
                            fontSize: "14px",
                            fontWeight: "500",
                            minWidth: "120px"
                        },
                        onclick: () => {
                            document.body.removeChild(overlay);
                            resolve('save');
                        }
                    }),
                    $el("button", {
                        textContent: "Discard Changes",
                        style: {
                            padding: "10px 20px",
                            backgroundColor: "#dc3545",
                            color: "white",
                            border: "none",
                            borderRadius: "4px",
                            cursor: "pointer",
                            fontSize: "14px",
                            fontWeight: "500",
                            minWidth: "120px"
                        },
                        onclick: () => {
                            document.body.removeChild(overlay);
                            resolve('discard');
                        }
                    }),
                    $el("button", {
                        textContent: "Cancel",
                        style: {
                            padding: "10px 20px",
                            backgroundColor: "#6c757d",
                            color: "white",
                            border: "none",
                            borderRadius: "4px",
                            cursor: "pointer",
                            fontSize: "14px",
                            fontWeight: "500",
                            minWidth: "120px"
                        },
                        onclick: () => {
                            document.body.removeChild(overlay);
                            resolve('cancel');
                        }
                    })
                ])
            ]);
            
            const overlay = $el("div", {
                style: {
                    position: "fixed",
                    top: "0",
                    left: "0",
                    width: "100%",
                    height: "100%",
                    backgroundColor: "rgba(0,0,0,0.5)",
                    zIndex: "10002"
                },
                onclick: (e) => {
                    // Only close if clicking on overlay, not dialog
                    if (e.target === overlay) {
                        document.body.removeChild(overlay);
                        resolve('cancel');
                    }
                }
            }, [dialog]);
            
            document.body.appendChild(overlay);
            
            // Focus the "Save Changes" button by default
            const saveButton = dialog.querySelector('button');
            if (saveButton) {
                saveButton.focus();
            }
        });
    }

    /**
     * Show confirmation dialog using ComfyUI's native API
     */
    async showConfirmDialog(message) {
        // Try ComfyUI's native confirm dialog first
        if (typeof app !== 'undefined' && app.extensionManager && app.extensionManager.dialog && app.extensionManager.dialog.confirm) {
            try {
                return await app.extensionManager.dialog.confirm({
                    title: "Confirm",
                    message: message
                });
            } catch (error) {
                console.warn("ComfyUI extensionManager dialog.confirm failed, falling back to browser confirm:", error);
            }
        }
        
        // Fallback to browser confirm
        return confirm(message);
    }
    
    /**
     * Show alert dialog using ComfyUI's native API or notification
     */
    async showAlertDialog(message) {
        // Try ComfyUI's notification system first
        if (typeof app !== 'undefined' && app.ui && app.ui.dialog && app.ui.dialog.show) {
            try {
                app.ui.dialog.show(message);
                return;
            } catch (error) {
                console.warn("ComfyUI ui.dialog.show failed, falling back to alert:", error);
            }
        }
        
        // Fallback to browser alert
        alert(message);
    }
}

// Dialog instance management
let editDialog = null;

/**
 * Show the edit dialog
 */
function showPromptEditDialog(subprompt = null) {
    if (!editDialog) {
        editDialog = new PromptEditDialog();
        // Update the global reference
        window.PromptCompanion.editDialog = editDialog;
    }
    editDialog.show(subprompt);
}

/**
 * Hide the edit dialog
 */
function hidePromptEditDialog() {
    if (editDialog) {
        editDialog.hide();
    }
}

/**
 * Get the current edit dialog instance
 */
function getEditDialog() {
    return editDialog;
}

// Context menu integration is handled by extensions.js to avoid conflicts

// Export functions for use by other components
window.PromptCompanion = window.PromptCompanion || {};
window.PromptCompanion.showEditDialog = showPromptEditDialog;
window.PromptCompanion.hideEditDialog = hidePromptEditDialog;
window.PromptCompanion.getEditDialog = getEditDialog;
window.PromptCompanion.editDialog = null; // Will be set when dialog is created