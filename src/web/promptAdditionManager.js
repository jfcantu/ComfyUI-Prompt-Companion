import { $el, ComfyDialog } from "../../../../scripts/ui.js";
import { app } from "../../../../scripts/app.js";
import { ApiOperations } from "./api-operations.js";

class PromptAdditionManager extends ComfyDialog {
    constructor(promptAdditionsData = {}, node = null, currentAdditionName = null) {
        super();
        this.element.classList.add("comfy-prompt-addition-manager");
        
        // Handle both old format (direct object) and new format (object with prompt_additions/prompt_groups)
        if (promptAdditionsData.prompt_additions) {
            this.promptAdditions = {};
            for (const addition of promptAdditionsData.prompt_additions) {
                this.promptAdditions[addition.name] = addition;
            }
            this.promptGroups = promptAdditionsData.prompt_groups || [];
        } else {
            // Backward compatibility - old format
            this.promptAdditions = promptAdditionsData;
            this.promptGroups = [];
        }
        
        this.node = node;
        this.currentAdditionName = currentAdditionName;
        this.selectedAdditionName = currentAdditionName;
        this.selectedGroupId = null; // Track selected group for filtering
        this.originalAdditionData = {};
        
        this.content = $el(
            "div",
            {
                style: {
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr",
                    gap: "15px",
                    minWidth: "800px",
                    minHeight: "500px",
                },
                className: "prompt-addition-manager-content",
            },
            [
                // Left half - Prompt Groups
                $el("div", {
                    style: {
                        display: "flex",
                        flexDirection: "column",
                        gap: "15px",
                    }
                }, [
                    $el("h3", {
                        textContent: "Prompt Groups",
                        style: {
                            margin: "0",
                            textAlign: "center",
                            fontSize: "16px",
                            fontWeight: "bold",
                        }
                    }),
                    // Prompt Groups list
                    $el("div", {
                        style: {
                            display: "flex",
                            flexDirection: "column",
                            gap: "5px",
                        }
                    }, [
                        (this.groupsList = $el("div", {
                            style: {
                                border: "1px solid #666",
                                borderRadius: "4px",
                                height: "150px",
                                overflowY: "auto",
                                padding: "5px",
                                backgroundColor: "#2a2a2a",
                            },
                            className: "prompt-groups-list"
                        })),
                        // Group buttons
                        $el("div", {
                            style: {
                                display: "flex",
                                gap: "5px",
                            }
                        }, [
                            (this.createGroupButton = $el("button", {
                                type: "button",
                                textContent: "Create New",
                                onclick: () => this.createNewGroup(),
                                style: {
                                    padding: "6px 12px",
                                    backgroundColor: "#28a745",
                                    color: "white",
                                    border: "none",
                                    borderRadius: "4px",
                                    cursor: "pointer",
                                    fontSize: "11px",
                                    flex: "1",
                                }
                            })),
                            (this.deleteGroupButton = $el("button", {
                                type: "button",
                                textContent: "Delete",
                                onclick: () => this.deleteSelectedGroup(),
                                disabled: true,
                                style: {
                                    padding: "6px 12px",
                                    backgroundColor: "#dc3545",
                                    color: "white",
                                    border: "none",
                                    borderRadius: "4px",
                                    cursor: "pointer",
                                    fontSize: "11px",
                                    flex: "1",
                                }
                            }))
                        ])
                    ]),
                    // Prompt Group editing frame (initially hidden)
                    (this.groupEditFrame = $el("div", {
                        style: {
                            border: "2px solid #666",
                            borderRadius: "6px",
                            padding: "10px",
                            backgroundColor: "#1e1e1e",
                            display: "none",
                        }
                    }, [
                        $el("h4", {
                            textContent: "Prompt Group",
                            style: {
                                margin: "0 0 10px 0",
                                fontSize: "14px",
                                fontWeight: "bold",
                                textAlign: "center",
                            }
                        }),
                        // Group name field
                        $el("div", {
                            style: {
                                marginBottom: "10px",
                            }
                        }, [
                            $el("label", {
                                textContent: "Name:",
                                style: { 
                                    display: "block",
                                    fontWeight: "bold",
                                    marginBottom: "5px",
                                    fontSize: "12px",
                                }
                            }),
                            (this.groupNameInput = $el("input", {
                                type: "text",
                                placeholder: "Enter group name...",
                                style: {
                                    width: "100%",
                                    padding: "6px",
                                    borderRadius: "4px",
                                    border: "1px solid #666",
                                    backgroundColor: "#2a2a2a",
                                    color: "white",
                                }
                            }))
                        ]),
                        // Group trigger words field
                        $el("div", {
                            style: {
                                marginBottom: "10px",
                            }
                        }, [
                            $el("label", {
                                textContent: "Trigger Words (comma separated):",
                                style: { 
                                    display: "block",
                                    fontWeight: "bold",
                                    marginBottom: "5px",
                                    fontSize: "12px",
                                }
                            }),
                            (this.groupTriggerWordsInput = $el("textarea", {
                                placeholder: "Enter trigger words separated by commas...",
                                style: {
                                    width: "100%",
                                    minHeight: "60px",
                                    padding: "6px",
                                    borderRadius: "4px",
                                    border: "1px solid #666",
                                    backgroundColor: "#2a2a2a",
                                    color: "white",
                                    resize: "vertical",
                                }
                            }))
                        ]),
                        // Group save buttons
                        $el("div", {
                            style: {
                                display: "flex",
                                gap: "5px",
                                justifyContent: "center",
                            }
                        }, [
                            (this.saveGroupButton = $el("button", {
                                type: "button",
                                textContent: "OK",
                                onclick: () => this.saveCurrentGroupAndClear(),
                                style: {
                                    padding: "6px 12px",
                                    backgroundColor: "#007bff",
                                    color: "white",
                                    border: "none",
                                    borderRadius: "4px",
                                    cursor: "pointer",
                                    fontSize: "11px",
                                }
                            })),
                            (this.renameGroupButton = $el("button", {
                                type: "button",
                                textContent: "Rename",
                                onclick: () => this.renameSelectedGroup(),
                                disabled: true,
                                style: {
                                    padding: "6px 12px",
                                    backgroundColor: "#ffc107",
                                    color: "white",
                                    border: "none",
                                    borderRadius: "4px",
                                    cursor: "pointer",
                                    fontSize: "11px",
                                }
                            })),
                            (this.revertGroupButton = $el("button", {
                                type: "button",
                                textContent: "Cancel",
                                onclick: () => this.cancelGroupSelection(),
                                disabled: true,
                                style: {
                                    padding: "6px 12px",
                                    backgroundColor: "#6c757d",
                                    color: "white",
                                    border: "none",
                                    borderRadius: "4px",
                                    cursor: "pointer",
                                    fontSize: "11px",
                                }
                            }))
                        ])
                    ]))
                ]),
                // Right half - Prompt Additions
                $el("div", {
                    style: {
                        display: "flex",
                        flexDirection: "column",
                        gap: "15px",
                    }
                }, [
                    $el("h3", {
                        textContent: "Prompt Additions",
                        style: {
                            margin: "0",
                            textAlign: "center",
                            fontSize: "16px",
                            fontWeight: "bold",
                        }
                    }),
                    // Prompt Additions list
                    $el("div", {
                        style: {
                            display: "flex",
                            flexDirection: "column",
                            gap: "5px",
                        }
                    }, [
                        (this.additionsList = $el("div", {
                            style: {
                                border: "1px solid #666",
                                borderRadius: "4px",
                                height: "150px",
                                overflowY: "auto",
                                padding: "5px",
                                backgroundColor: "#2a2a2a",
                            },
                            className: "prompt-additions-list"
                        })),
                        // Addition buttons
                        $el("div", {
                            style: {
                                display: "flex",
                                gap: "5px",
                            }
                        }, [
                            $el("button", {
                                type: "button",
                                textContent: "Create New",
                                onclick: () => this.createNew(),
                                style: {
                                    padding: "6px 12px",
                                    backgroundColor: "#28a745",
                                    color: "white",
                                    border: "none",
                                    borderRadius: "4px",
                                    cursor: "pointer",
                                    fontSize: "11px",
                                    flex: "1",
                                }
                            }),
                            (this.deleteButton = $el("button", {
                                type: "button",
                                textContent: "Delete",
                                onclick: () => this.deleteSelected(),
                                disabled: true,
                                style: {
                                    padding: "6px 12px",
                                    backgroundColor: "#dc3545",
                                    color: "white",
                                    border: "none",
                                    borderRadius: "4px",
                                    cursor: "pointer",
                                    fontSize: "11px",
                                    flex: "1",
                                }
                            }))
                        ])
                    ]),
                    // Prompt Addition editing frame
                    $el("div", {
                        style: {
                            border: "2px solid #666",
                            borderRadius: "6px",
                            padding: "10px",
                            backgroundColor: "#1e1e1e",
                        }
                    }, [
                        $el("h4", {
                            textContent: "Prompt Addition",
                            style: {
                                margin: "0 0 10px 0",
                                fontSize: "14px",
                                fontWeight: "bold",
                                textAlign: "center",
                            }
                        }),
                        $el("div", {
                            style: {
                                display: "grid",
                                gridTemplateColumns: "1fr 1fr",
                                gap: "10px",
                                marginBottom: "10px",
                            }
                        }, [
                            // Left column - Positive
                            $el("div", {
                                style: {
                                    display: "flex",
                                    flexDirection: "column",
                                    gap: "5px",
                                }
                            }, [
                                $el("label", {
                                    textContent: "Positive:",
                                    style: { 
                                        fontWeight: "bold",
                                        fontSize: "12px",
                                    }
                                }),
                                (this.positiveTextarea = $el("textarea", {
                                    placeholder: "Enter positive prompt additions...",
                                    style: {
                                        minHeight: "80px",
                                        resize: "vertical",
                                        fontSize: "11px",
                                    }
                                })),
                                (this.revertPositiveButton = $el("button", {
                                    type: "button",
                                    textContent: "Revert",
                                    onclick: () => this.revertPositiveToSaved(),
                                    disabled: true,
                                    style: {
                                        padding: "3px 6px",
                                        fontSize: "10px",
                                    }
                                }))
                            ]),
                            // Right column - Negative  
                            $el("div", {
                                style: {
                                    display: "flex",
                                    flexDirection: "column",
                                    gap: "5px",
                                }
                            }, [
                                $el("label", {
                                    textContent: "Negative:",
                                    style: { 
                                        fontWeight: "bold",
                                        fontSize: "12px",
                                    }
                                }),
                                (this.negativeTextarea = $el("textarea", {
                                    placeholder: "Enter negative prompt additions...",
                                    style: {
                                        minHeight: "80px",
                                        resize: "vertical",
                                        fontSize: "11px",
                                    }
                                })),
                                (this.revertNegativeButton = $el("button", {
                                    type: "button",
                                    textContent: "Revert",
                                    onclick: () => this.revertNegativeToSaved(),
                                    disabled: true,
                                    style: {
                                        padding: "3px 6px",
                                        fontSize: "10px",
                                    }
                                }))
                            ])
                        ]),
                        // Addition save buttons
                        $el("div", {
                            style: {
                                display: "flex",
                                justifyContent: "center",
                                gap: "10px",
                            }
                        }, [
                            (this.saveButton = $el("button", {
                                type: "button",
                                textContent: "Save",
                                onclick: () => this.saveCurrentAddition(),
                                disabled: false,
                                style: {
                                    padding: "6px 15px",
                                    backgroundColor: "#007bff",
                                    color: "white",
                                    border: "none",
                                    borderRadius: "4px",
                                    cursor: "pointer",
                                    fontSize: "11px",
                                }
                            })),
                            (this.saveAsButton = $el("button", {
                                type: "button",
                                textContent: "Save As...",
                                onclick: () => this.saveAsNewAddition(),
                                disabled: false,
                                style: {
                                    padding: "6px 15px",
                                    backgroundColor: "#28a745",
                                    color: "white",
                                    border: "none",
                                    borderRadius: "4px",
                                    cursor: "pointer",
                                    fontSize: "11px",
                                }
                            })),
                            (this.renameButton = $el("button", {
                                type: "button",
                                textContent: "Rename",
                                onclick: () => this.renameSelectedAddition(),
                                disabled: true,
                                style: {
                                    padding: "6px 15px",
                                    backgroundColor: "#ffc107",
                                    color: "white",
                                    border: "none",
                                    borderRadius: "4px",
                                    cursor: "pointer",
                                    fontSize: "11px",
                                }
                            }))
                        ])
                    ])
                ])
            ]
        );
        
        // Add status div at the bottom
        this.content.appendChild((this.statusDiv = $el("div", {
            style: {
                textAlign: "center",
                fontSize: "12px",
                color: "#666",
                minHeight: "20px",
                gridColumn: "1 / -1",
                marginTop: "10px",
            }
        })));
        
        this.populateGroupsList();
        this.populateAdditionsList();
    }

    createButtons() {
        // Create horizontal button container
        return [
            $el("div", {
                style: {
                    display: "flex",
                    gap: "10px",
                    justifyContent: "flex-end",
                    marginTop: "15px",
                }
            }, [
                $el("button", {
                    type: "button",
                    textContent: "Cancel",
                    onclick: () => this.close(),
                    style: {
                        padding: "8px 16px",
                        border: "1px solid #6c757d",
                        borderRadius: "4px",
                        cursor: "pointer",
                        backgroundColor: "#6c757d",
                        color: "white",
                    }
                }),
                (this.okButton = $el("button", {
                    type: "button",
                    textContent: "OK",
                    onclick: () => this.saveAndClose(),
                    disabled: true,
                    style: {
                        padding: "8px 16px",
                        backgroundColor: "#28a745",
                        color: "white",
                        border: "none",
                        borderRadius: "4px",
                        cursor: "pointer",
                    }
                }))
            ])
        ];
    }

    async deleteSelected() {
        if (!this.selectedAdditionName) {
            this.updateStatus("No addition selected", "error");
            return;
        }

        if (app.extensionManager && app.extensionManager.dialog && app.extensionManager.dialog.confirm) {
            const confirmed = await app.extensionManager.dialog.confirm({
                title: "Confirm Delete",
                message: `Are you sure you want to delete "${this.selectedAdditionName}"?`,
                type: "delete"
            });
            
            if (!confirmed) {
                return;
            }
        } else {
            const confirmed = await this.comfyConfirm(
                "Confirm Delete",
                `Are you sure you want to delete "${this.selectedAdditionName}"?`,
                "Delete",
                "Cancel"
            );
            
            if (!confirmed) {
                return;
            }
        }

        try {
            this.updateStatus("Deleting prompt addition...", "info");
            const deletedName = this.selectedAdditionName;
            await ApiOperations.deletePromptAddition(this.selectedAdditionName);
            
            // Remove from local collection
            delete this.promptAdditions[deletedName];
            
            // Find an alternative addition to select
            const remainingAdditions = Object.keys(this.promptAdditions);
            let nextSelection = null;
            
            if (remainingAdditions.length > 0) {
                // Try to find the node's original selection if different from deleted one
                if (this.currentAdditionName && 
                    this.currentAdditionName !== deletedName && 
                    this.promptAdditions[this.currentAdditionName]) {
                    nextSelection = this.currentAdditionName;
                } else {
                    // Otherwise, just select the first available addition
                    nextSelection = remainingAdditions[0];
                }
            }
            
            // Clear current UI state
            this.positiveTextarea.value = "";
            this.negativeTextarea.value = "";
            this.selectedAdditionName = null;
            this.originalAdditionData = {};
            
            // Refresh the list first
            this.populateAdditionsList();
            
            if (nextSelection) {
                // Select the next available addition
                this.selectAddition(nextSelection);
                
                // Update the node's widget if we have a node reference
                if (this.node && this.node.promptAdditionNameWidget) {
                    this.node.promptAdditionNameWidget.value = nextSelection;
                    if (this.node.promptAdditionNameWidget.callback) {
                        this.node.promptAdditionNameWidget.callback();
                    }
                }
            } else {
                // No additions left - disable buttons that require a selection
                this.deleteButton.disabled = true;
                this.revertPositiveButton.disabled = true;
                this.revertNegativeButton.disabled = true;
                this.renameButton.disabled = true;
                this.okButton.disabled = false; // OK can still close dialog
            }
            
            this.updateStatus("Prompt addition deleted successfully", "success");
        } catch (error) {
            this.updateStatus("Failed to delete prompt addition", "error");
            console.error("Error deleting prompt addition:", error);
        }
    }

    async saveCurrentAddition() {
        const positiveText = this.positiveTextarea.value.trim();
        const negativeText = this.negativeTextarea.value.trim();
        
        if (!this.selectedAdditionName) {
            // No addition selected, prompt for name and create new
            const name = await this.promptForName("Save New Prompt Addition", "Enter name for new prompt addition:");
            
            if (!name) {
                this.updateStatus("Save cancelled", "info");
                return;
            }
            
            // Check if name already exists
            if (this.promptAdditions[name]) {
                this.updateStatus(`Name "${name}" already exists`, "error");
                return;
            }
            
            // Create new addition
            const promptAddition = {
                name: name.trim(),
                trigger_words: "", // Not implemented yet
                positive_prompt_addition_text: positiveText,
                negative_prompt_addition_text: negativeText
                // ID will be assigned by the server
            };
            
            try {
                this.updateStatus("Saving new prompt addition...", "info");
                const response = await ApiOperations.writePromptAddition(promptAddition);
                
                // Update local collection with server response (includes IDs and groups)
                if (response && response.prompt_additions) {
                    this.promptAdditions = {};
                    for (const addition of response.prompt_additions) {
                        this.promptAdditions[addition.name] = addition;
                    }
                    this.promptGroups = response.prompt_groups || [];
                } else {
                    // Fallback: just add to local collection
                    this.promptAdditions[name] = promptAddition;
                }
                
                // Refresh the list
                this.populateAdditionsList();
                
                // Select the new addition
                this.selectAddition(name);
                
                // Update the node's selected addition if we have a node reference
                if (this.node) {
                    if (this.node.promptAdditionNameWidget) {
                        this.node.promptAdditionNameWidget.value = name;
                        if (this.node.promptAdditionNameWidget.callback) {
                            this.node.promptAdditionNameWidget.callback();
                        }
                    }
                }
                
                this.updateStatus(`Created "${name}" successfully`, "success");
            } catch (error) {
                this.updateStatus("Failed to create prompt addition", "error");
                console.error("Error creating prompt addition:", error);
            }
            return;
        }

        // Update existing addition
        const currentAddition = this.promptAdditions[this.selectedAdditionName];
        const promptAddition = {
            id: currentAddition.id,
            name: this.selectedAdditionName,
            trigger_words: "", // Not implemented yet
            positive_prompt_addition_text: positiveText,
            negative_prompt_addition_text: negativeText
        };

        try {
            this.updateStatus("Saving prompt addition...", "info");
            const response = await ApiOperations.writePromptAddition(promptAddition);
            
            // Update local collection with server response
            if (response && response.prompt_additions) {
                this.promptAdditions = {};
                for (const addition of response.prompt_additions) {
                    this.promptAdditions[addition.name] = addition;
                }
                this.promptGroups = response.prompt_groups || [];
            } else {
                // Fallback: just update local collection
                this.promptAdditions[this.selectedAdditionName] = promptAddition;
            }
            
            // Update original data
            this.originalAdditionData = {
                name: promptAddition.name,
                trigger_words: promptAddition.trigger_words,
                positive_prompt_addition_text: promptAddition.positive_prompt_addition_text,
                negative_prompt_addition_text: promptAddition.negative_prompt_addition_text
            };
            
            // Update the node's widgets if this is the currently selected addition
            if (this.node && this.node.promptAdditionNameWidget?.value === this.selectedAdditionName) {
                if (this.node.positiveAdditionWidget) {
                    this.node.positiveAdditionWidget.value = positiveText;
                }
                if (this.node.negativeAdditionWidget) {
                    this.node.negativeAdditionWidget.value = negativeText;
                }
            }
            
            this.updateStatus("Prompt addition saved successfully", "success");
        } catch (error) {
            this.updateStatus("Failed to save prompt addition", "error");
            console.error("Error saving prompt addition:", error);
        }
    }

    async saveAsNewAddition() {
        const positiveText = this.positiveTextarea.value.trim();
        const negativeText = this.negativeTextarea.value.trim();
        
        // Prompt for a new name
        const name = await this.promptForName("Save As New Prompt Addition", "Enter name for new prompt addition:");
        
        if (!name) {
            this.updateStatus("Save As cancelled", "info");
            return;
        }
        
        // Check if name already exists
        if (this.promptAdditions[name]) {
            this.updateStatus(`Name "${name}" already exists`, "error");
            return;
        }
        
        // Create new addition
        const promptAddition = {
            name: name.trim(),
            trigger_words: "", // Not implemented yet
            positive_prompt_addition_text: positiveText,
            negative_prompt_addition_text: negativeText
            // ID will be assigned by the server
        };
        
        try {
            this.updateStatus("Saving new prompt addition...", "info");
            const response = await ApiOperations.writePromptAddition(promptAddition);
            
            // Update local collection with server response
            if (response && response.prompt_additions) {
                this.promptAdditions = {};
                for (const addition of response.prompt_additions) {
                    this.promptAdditions[addition.name] = addition;
                }
                this.promptGroups = response.prompt_groups || [];
            } else {
                // Fallback: just add to local collection
                this.promptAdditions[name] = promptAddition;
            }
            
            // Refresh the list
            this.populateAdditionsList();
            
            // Select the new addition
            this.selectAddition(name);
            
            // Update the node's selected addition if we have a node reference
            if (this.node) {
                if (this.node.promptAdditionNameWidget) {
                    this.node.promptAdditionNameWidget.value = name;
                    if (this.node.promptAdditionNameWidget.callback) {
                        this.node.promptAdditionNameWidget.callback();
                    }
                }
            }
            
            this.updateStatus(`Created "${name}" successfully`, "success");
        } catch (error) {
            this.updateStatus("Failed to create prompt addition", "error");
            console.error("Error creating prompt addition:", error);
        }
    }

    revertPositiveToSaved() {
        if (!this.selectedAdditionName || !this.originalAdditionData.name) {
            this.updateStatus("No addition selected or no saved data", "error");
            return;
        }

        // Restore original positive text
        this.positiveTextarea.value = this.originalAdditionData.positive_prompt_addition_text || "";
        this.updateStatus("Reverted positive text to saved version", "info");
    }

    revertNegativeToSaved() {
        if (!this.selectedAdditionName || !this.originalAdditionData.name) {
            this.updateStatus("No addition selected or no saved data", "error");
            return;
        }

        // Restore original negative text
        this.negativeTextarea.value = this.originalAdditionData.negative_prompt_addition_text || "";
        this.updateStatus("Reverted negative text to saved version", "info");
    }

    async saveAndClose() {
        // Check if we're in group edit mode
        if (this.selectedGroupId !== null) {
            // In group mode - save any group changes
            try {
                await this.saveCurrentGroup();
            } catch (error) {
                console.error("Error saving group:", error);
                // Don't prevent closing if save fails
            }
        } else if (this.selectedAdditionName) {
            // If an addition is selected, save it first
            try {
                await this.saveCurrentAddition();
            } catch (error) {
                console.error("Error saving addition:", error);
                // Don't prevent closing if save fails
            }
        } else {
            // No addition selected - check if user has unsaved changes
            const positiveText = this.positiveTextarea.value.trim();
            const negativeText = this.negativeTextarea.value.trim();
            
            if (positiveText || negativeText) {
                // User has unsaved text, offer to save
                const shouldSave = await this.comfyConfirm(
                    "Unsaved Changes", 
                    "You have unsaved text in the prompt fields. Would you like to save it as a new prompt addition before closing?",
                    "Save", 
                    "Discard"
                );
                
                if (shouldSave) {
                    try {
                        await this.saveCurrentAddition();
                    } catch (error) {
                        console.error("Error saving addition:", error);
                        // Continue with closing even if save fails
                    }
                }
            }
        }
        
        // Close the dialog
        this.close();
    }

    updateStatus(message, type = "info") {
        this.statusDiv.textContent = message;
        this.statusDiv.style.color = type === "error" ? "#ff4444" : 
                                    type === "success" ? "#44aa44" : "#666";
    }

    /**
     * ComfyUI-style confirmation dialog
     */
    comfyConfirm(title, message, confirmText = "Confirm", cancelText = "Cancel") {
        return new Promise((resolve) => {
            // Create overlay
            const modalOverlay = document.createElement('div');
            modalOverlay.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0, 0, 0, 0.8);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 1101;
            `;

            // Create dialog
            const modalDialog = document.createElement('div');
            modalDialog.style.cssText = `
                background-color: #333;
                padding: 20px;
                border-radius: 4px;
                max-width: 400px;
                width: 80%;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.5);
                color: #fff;
            `;

            // Title
            const modalTitle = document.createElement('h3');
            modalTitle.textContent = title;
            modalTitle.style.cssText = `
                margin: 0 0 15px 0;
                color: #fff;
                font-size: 16px;
            `;

            // Message
            const modalMessage = document.createElement('p');
            modalMessage.textContent = message;
            modalMessage.style.cssText = `
                margin: 0 0 20px 0;
                word-break: break-word;
                line-height: 1.4;
            `;

            // Button container
            const modalButtons = document.createElement('div');
            modalButtons.style.cssText = `
                display: flex;
                justify-content: flex-end;
                gap: 10px;
            `;

            // Cancel button
            const cancelButton = document.createElement('button');
            cancelButton.textContent = cancelText;
            cancelButton.style.cssText = `
                padding: 8px 16px;
                border: 1px solid #6c757d;
                border-radius: 4px;
                background-color: #6c757d;
                color: white;
                cursor: pointer;
            `;
            cancelButton.onclick = () => {
                document.body.removeChild(modalOverlay);
                resolve(false);
            };

            // Confirm button
            const confirmButton = document.createElement('button');
            confirmButton.textContent = confirmText;
            confirmButton.style.cssText = `
                padding: 8px 16px;
                border: 1px solid #28a745;
                border-radius: 4px;
                background-color: #28a745;
                color: white;
                cursor: pointer;
            `;
            confirmButton.onclick = () => {
                document.body.removeChild(modalOverlay);
                resolve(true);
            };

            // Close on overlay click
            modalOverlay.onclick = (e) => {
                if (e.target === modalOverlay) {
                    document.body.removeChild(modalOverlay);
                    resolve(false);
                }
            };

            // Escape key handler
            const keyHandler = (e) => {
                if (e.key === 'Escape') {
                    document.body.removeChild(modalOverlay);
                    document.removeEventListener('keydown', keyHandler);
                    resolve(false);
                }
            };
            document.addEventListener('keydown', keyHandler);

            // Assemble dialog
            modalButtons.appendChild(cancelButton);
            modalButtons.appendChild(confirmButton);
            modalDialog.appendChild(modalTitle);
            modalDialog.appendChild(modalMessage);
            modalDialog.appendChild(modalButtons);
            modalOverlay.appendChild(modalDialog);
            document.body.appendChild(modalOverlay);

            // Focus confirm button
            confirmButton.focus();
        });
    }

    /**
     * ComfyUI-style prompt dialog
     */
    comfyPrompt(title, message, defaultValue = "") {
        return new Promise((resolve) => {
            // Create overlay
            const modalOverlay = document.createElement('div');
            modalOverlay.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0, 0, 0, 0.8);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 1101;
            `;

            // Create dialog
            const modalDialog = document.createElement('div');
            modalDialog.style.cssText = `
                background-color: #333;
                padding: 20px;
                border-radius: 4px;
                max-width: 400px;
                width: 80%;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.5);
                color: #fff;
            `;

            // Title
            const modalTitle = document.createElement('h3');
            modalTitle.textContent = title;
            modalTitle.style.cssText = `
                margin: 0 0 15px 0;
                color: #fff;
                font-size: 16px;
            `;

            // Message
            const modalMessage = document.createElement('p');
            modalMessage.textContent = message;
            modalMessage.style.cssText = `
                margin: 0 0 15px 0;
                word-break: break-word;
                line-height: 1.4;
            `;

            // Input field
            const inputField = document.createElement('input');
            inputField.type = 'text';
            inputField.value = defaultValue;
            inputField.style.cssText = `
                width: 100%;
                padding: 8px;
                margin-bottom: 20px;
                border: 1px solid #555;
                border-radius: 4px;
                background-color: #444;
                color: #fff;
                box-sizing: border-box;
            `;

            // Button container
            const modalButtons = document.createElement('div');
            modalButtons.style.cssText = `
                display: flex;
                justify-content: flex-end;
                gap: 10px;
            `;

            // Cancel button
            const cancelButton = document.createElement('button');
            cancelButton.textContent = 'Cancel';
            cancelButton.style.cssText = `
                padding: 8px 16px;
                border: 1px solid #6c757d;
                border-radius: 4px;
                background-color: #6c757d;
                color: white;
                cursor: pointer;
            `;
            cancelButton.onclick = () => {
                document.body.removeChild(modalOverlay);
                resolve(null);
            };

            // OK button
            const okButton = document.createElement('button');
            okButton.textContent = 'OK';
            okButton.style.cssText = `
                padding: 8px 16px;
                border: 1px solid #28a745;
                border-radius: 4px;
                background-color: #28a745;
                color: white;
                cursor: pointer;
            `;
            okButton.onclick = () => {
                const value = inputField.value.trim();
                document.body.removeChild(modalOverlay);
                resolve(value || null);
            };

            // Enter key handler
            inputField.onkeydown = (e) => {
                if (e.key === 'Enter') {
                    okButton.click();
                }
            };

            // Close on overlay click
            modalOverlay.onclick = (e) => {
                if (e.target === modalOverlay) {
                    document.body.removeChild(modalOverlay);
                    resolve(null);
                }
            };

            // Escape key handler
            const keyHandler = (e) => {
                if (e.key === 'Escape') {
                    document.body.removeChild(modalOverlay);
                    document.removeEventListener('keydown', keyHandler);
                    resolve(null);
                }
            };
            document.addEventListener('keydown', keyHandler);

            // Assemble dialog
            modalButtons.appendChild(cancelButton);
            modalButtons.appendChild(okButton);
            modalDialog.appendChild(modalTitle);
            modalDialog.appendChild(modalMessage);
            modalDialog.appendChild(inputField);
            modalDialog.appendChild(modalButtons);
            modalOverlay.appendChild(modalDialog);
            document.body.appendChild(modalOverlay);

            // Focus and select input
            inputField.focus();
            inputField.select();
        });
    }

    /**
     * ComfyUI-style notification
     */
    comfyNotify(message, type = "info", duration = 3000) {
        const notification = document.createElement('div');
        const bgColor = type === "error" ? "#dc3545" : 
                       type === "success" ? "#28a745" : 
                       type === "warning" ? "#ffc107" : "#17a2b8";
        
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background-color: ${bgColor};
            color: white;
            padding: 12px 20px;
            border-radius: 4px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
            z-index: 1102;
            max-width: 300px;
            word-break: break-word;
            font-size: 14px;
        `;
        
        notification.textContent = message;
        document.body.appendChild(notification);
        
        // Auto-remove after duration
        setTimeout(() => {
            if (document.body.contains(notification)) {
                document.body.removeChild(notification);
            }
        }, duration);
        
        return notification;
    }

    populateAdditionsList() {
        this.additionsList.innerHTML = "";
        
        const additionNames = Object.keys(this.promptAdditions);
        
        if (additionNames.length === 0) {
            const emptyItem = $el("div", {
                textContent: "No additions found",
                style: {
                    padding: "8px",
                    color: "#999",
                    fontStyle: "italic",
                    textAlign: "center",
                }
            });
            this.additionsList.appendChild(emptyItem);
            return;
        }
        
        // Get selected additions for the current group
        let selectedAdditionIds = new Set();
        if (this.selectedGroupId !== null) {
            const selectedGroup = this.promptGroups.find(g => g.id === this.selectedGroupId);
            if (selectedGroup && selectedGroup.additions) {
                selectedAdditionIds = new Set(selectedGroup.additions.map(a => a.addition_id));
            }
        }
        
        additionNames.forEach(name => {
            const addition = this.promptAdditions[name];
            const isSelected = this.selectedGroupId !== null && 
                              addition && addition.id && 
                              selectedAdditionIds.has(addition.id);
            
            const item = $el("div", {
                textContent: name,
                style: {
                    padding: "8px",
                    cursor: "pointer",
                    borderRadius: "3px",
                    marginBottom: "2px",
                    backgroundColor: isSelected ? "#28a745" : "#3a3a3a",
                    border: isSelected ? "1px solid #1e7e34" : "1px solid transparent",
                    transition: "all 0.2s",
                    color: isSelected ? "white" : "",
                },
                onclick: () => {
                    if (this.selectedGroupId !== null) {
                        this.toggleAdditionInGroup(name);
                    } else {
                        this.selectAddition(name);
                    }
                }
            });
            
            // Store addition ID for easy reference
            item.setAttribute('data-addition-name', name);
            if (isSelected) {
                item.classList.add('group-selected');
            }
            
            // Add hover effect
            item.addEventListener("mouseenter", () => {
                if (this.selectedGroupId !== null) {
                    // Group mode - show toggle effect
                    item.style.backgroundColor = isSelected ? "#218838" : "#4a4a4a";
                    item.style.borderColor = isSelected ? "#1e7e34" : "#666";
                } else {
                    // Individual mode - show selection effect
                    item.style.backgroundColor = "#4a4a4a";
                    item.style.borderColor = "#666";
                }
            });
            
            item.addEventListener("mouseleave", () => {
                if (this.selectedGroupId !== null) {
                    // Group mode - restore group selection state
                    const stillSelected = item.classList.contains('group-selected');
                    item.style.backgroundColor = stillSelected ? "#28a745" : "#3a3a3a";
                    item.style.borderColor = stillSelected ? "#1e7e34" : "transparent";
                } else {
                    // Individual mode - restore individual selection state
                    if (!item.classList.contains("selected")) {
                        item.style.backgroundColor = "#3a3a3a";
                        item.style.borderColor = "transparent";
                    }
                }
            });
            
            this.additionsList.appendChild(item);
        });
    }
    
    toggleAdditionInGroup(additionName) {
        if (this.selectedGroupId === null) return;
        
        const addition = this.promptAdditions[additionName];
        if (!addition || !addition.id) return;
        
        const groupIndex = this.promptGroups.findIndex(g => g.id === this.selectedGroupId);
        if (groupIndex === -1) return;
        
        const group = this.promptGroups[groupIndex];
        const additionIndex = group.additions.findIndex(a => a.addition_id === addition.id);
        
        if (additionIndex === -1) {
            // Add to group
            group.additions.push({
                addition_id: addition.id,
                priority: group.additions.length + 1
            });
        } else {
            // Remove from group
            group.additions.splice(additionIndex, 1);
            // Reorder priorities
            group.additions.forEach((a, i) => a.priority = i + 1);
        }
        
        // Update local data
        this.promptGroups[groupIndex] = group;
        
        // Refresh the list to show updated selections
        this.populateAdditionsList();
        
        // Update status
        const action = additionIndex === -1 ? "Added" : "Removed";
        this.updateStatus(`${action} "${additionName}" ${additionIndex === -1 ? "to" : "from"} group`, "info");
    }
    
    selectAddition(name) {
        // Remove previous selection
        const previousSelected = this.additionsList.querySelector(".selected");
        if (previousSelected) {
            previousSelected.classList.remove("selected");
            previousSelected.style.backgroundColor = "#3a3a3a";
            previousSelected.style.borderColor = "transparent";
        }
        
        // Add selection to clicked item
        const items = this.additionsList.children;
        for (let item of items) {
            if (item.textContent === name) {
                item.classList.add("selected");
                item.style.backgroundColor = "#007bff";
                item.style.borderColor = "#0056b3";
                break;
            }
        }
        
        // Update selected addition name
        this.selectedAdditionName = name;
        
        // Load the addition data
        const addition = this.promptAdditions[name];
        if (addition) {
            // Store original data for revert functionality
            this.originalAdditionData = {
                name: addition.name,
                trigger_words: addition.trigger_words || "",
                positive_prompt_addition_text: addition.positive_prompt_addition_text || "",
                negative_prompt_addition_text: addition.negative_prompt_addition_text || ""
            };
            
            // Load data into UI
            this.positiveTextarea.value = addition.positive_prompt_addition_text || "";
            this.negativeTextarea.value = addition.negative_prompt_addition_text || "";
            
            // Enable buttons
            this.deleteButton.disabled = false;
            this.saveButton.disabled = false;
            this.saveAsButton.disabled = false;
            this.renameButton.disabled = false;
            this.revertPositiveButton.disabled = false;
            this.revertNegativeButton.disabled = false;
            this.okButton.disabled = false;
            
            this.updateStatus(`Selected: ${name}`);
        }
    }
    
    clearSelection() {
        // Clear current selection
        this.selectedAdditionName = null;
        this.originalAdditionData = {};
        
        // Clear text boxes
        this.positiveTextarea.value = "";
        this.negativeTextarea.value = "";
        
        // Remove visual selection from list
        const previousSelected = this.additionsList.querySelector(".selected");
        if (previousSelected) {
            previousSelected.classList.remove("selected");
            previousSelected.style.backgroundColor = "#3a3a3a";
            previousSelected.style.borderColor = "transparent";
        }
        
        // Update button states
        this.deleteButton.disabled = true;
        this.renameButton.disabled = true;
        this.revertPositiveButton.disabled = true;
        this.revertNegativeButton.disabled = true;
        // Save and Save As buttons remain enabled (they can create new additions)
        // OK button remains enabled (can close dialog)
        
        this.updateStatus("Ready to create new prompt addition");
    }

    async createNew() {
        
        // First, clear the selection and text boxes for a fresh start
        this.clearSelection();
        
        try {
            const name = await this.promptForName("Create New Prompt Addition", "Enter name for new prompt addition:");
            
            if (!name) {
                return;
            }
            
            // Check if name already exists
            if (this.promptAdditions[name]) {
                this.updateStatus(`Name "${name}" already exists`, "error");
                return;
            }
            
            const positiveText = this.positiveTextarea.value.trim();
            const negativeText = this.negativeTextarea.value.trim();
            
            // Create the prompt addition object
            const promptAddition = {
                name: name.trim(),
                trigger_words: "", // Not implemented yet
                positive_prompt_addition_text: positiveText,
                negative_prompt_addition_text: negativeText
                // ID will be assigned by the server
            };
            
            
            this.updateStatus("Saving new prompt addition...", "info");
            
            const result = await ApiOperations.writePromptAddition(promptAddition);
            
            // Add to local collection
            this.promptAdditions[name] = promptAddition;
            
            // Refresh the list
            this.populateAdditionsList();
            
            // Select the newly created addition
            this.selectAddition(name);
            
            this.updateStatus(`Created "${name}" successfully`, "success");
        } catch (error) {
            this.updateStatus("Failed to create prompt addition", "error");
            console.error("Error in createNew:", error);
        }
    }
    
    async promptForName(title, message, defaultValue = "") {
        
        return new Promise((resolve) => {
            if (app.extensionManager && app.extensionManager.dialog && app.extensionManager.dialog.prompt) {
                app.extensionManager.dialog.prompt({
                    title: title,
                    message: message,
                    default: defaultValue
                }).then(result => {
                    resolve(result ? result.trim() : null);
                }).catch((error) => {
                    resolve(null);
                });
            } else {
                // Fallback to ComfyUI-style prompt
                this.comfyPrompt(title, message, defaultValue).then(result => {
                    resolve(result);
                }).catch((error) => {
                    resolve(null);
                });
            }
        });
    }

    populateGroupsList() {
        this.groupsList.innerHTML = "";
        
        // Add "(none)" option at the top
        const noneItem = $el("div", {
            textContent: "(none)",
            style: {
                padding: "8px",
                cursor: "pointer",
                borderRadius: "3px",
                marginBottom: "2px",
                backgroundColor: "#007bff", // Selected by default
                border: "1px solid #0056b3",
                transition: "all 0.2s",
                color: "white",
            },
            onclick: () => this.selectGroup(null)
        });
        noneItem.classList.add("selected");
        this.groupsList.appendChild(noneItem);
        
        // Add all prompt groups
        if (this.promptGroups && this.promptGroups.length > 0) {
            this.promptGroups.forEach(group => {
                const item = $el("div", {
                    textContent: group.name,
                    style: {
                        padding: "8px",
                        cursor: "pointer",
                        borderRadius: "3px",
                        marginBottom: "2px",
                        backgroundColor: "#3a3a3a",
                        border: "1px solid transparent",
                        transition: "all 0.2s",
                    },
                    onclick: () => this.selectGroup(group.id)
                });
                
                // Add hover effect
                item.addEventListener("mouseenter", () => {
                    item.style.backgroundColor = "#4a4a4a";
                    item.style.borderColor = "#666";
                });
                
                item.addEventListener("mouseleave", () => {
                    if (!item.classList.contains("selected")) {
                        item.style.backgroundColor = "#3a3a3a";
                        item.style.borderColor = "transparent";
                    }
                });
                
                this.groupsList.appendChild(item);
            });
        }
    }
    
    selectGroup(groupId) {
        // Remove previous selection
        const previousSelected = this.groupsList.querySelector(".selected");
        if (previousSelected) {
            previousSelected.classList.remove("selected");
            previousSelected.style.backgroundColor = "#3a3a3a";
            previousSelected.style.borderColor = "transparent";
            previousSelected.style.color = "";
        }
        
        // Add selection to clicked item
        const items = this.groupsList.children;
        for (let item of items) {
            const isNoneItem = item.textContent === "(none)";
            const isMatch = isNoneItem ? (groupId === null) : 
                           (this.promptGroups.find(g => g.name === item.textContent)?.id === groupId);
            
            if (isMatch) {
                item.classList.add("selected");
                item.style.backgroundColor = "#007bff";
                item.style.borderColor = "#0056b3";
                item.style.color = "white";
                break;
            }
        }
        
        // Update selected group ID
        this.selectedGroupId = groupId;
        
        // Show/hide group edit frame and update delete button
        if (groupId === null) {
            this.groupEditFrame.style.display = "none";
            this.deleteGroupButton.disabled = true;
        } else {
            this.groupEditFrame.style.display = "block";
            this.deleteGroupButton.disabled = false;
            this.loadGroupData(groupId);
        }
        
        // Clear individual addition selection when group is selected
        if (groupId !== null) {
            this.selectedAdditionName = null;
            this.positiveTextarea.value = "";
            this.negativeTextarea.value = "";
            this.deleteButton.disabled = true;
            this.revertPositiveButton.disabled = true;
            this.revertNegativeButton.disabled = true;
            // Keep OK button enabled in group mode so user can close dialog
            this.okButton.disabled = false;
        }
        
        // Refresh the additions list (now shows group selections)
        this.populateAdditionsList();
        
        // Update status
        if (groupId === null) {
            this.updateStatus("Individual addition mode - click to select additions for editing");
        } else {
            const groupName = this.promptGroups.find(g => g.id === groupId)?.name || "Unknown";
            const selectedGroup = this.promptGroups.find(g => g.id === groupId);
            const selectionCount = selectedGroup?.additions?.length || 0;
            this.updateStatus(`Group mode: ${groupName} - ${selectionCount} additions selected - click to toggle`);
        }
    }
    
    loadGroupData(groupId) {
        const group = this.promptGroups.find(g => g.id === groupId);
        if (group) {
            this.groupNameInput.value = group.name || "";
            this.groupTriggerWordsInput.value = (group.trigger_words || []).join(", ");
            this.selectedGroup = { ...group }; // Store original data for revert
            this.saveGroupButton.disabled = false;
            this.revertGroupButton.disabled = false;
            this.renameGroupButton.disabled = false;
        }
    }
    
    async createNewGroup() {
        const name = await this.promptForName("Create New Prompt Group", "Enter name for new prompt group:");
        
        if (!name) {
            this.updateStatus("Group creation cancelled", "info");
            return;
        }
        
        // Check if name already exists
        if (this.promptGroups.find(g => g.name === name)) {
            this.updateStatus(`Group name "${name}" already exists`, "error");
            return;
        }
        
        // Create new group object
        const newGroup = {
            id: this.getNextGroupId(),
            name: name.trim(),
            trigger_words: [],
            additions: []
        };
        
        try {
            this.updateStatus("Creating new prompt group...", "info");
            const response = await ApiOperations.writePromptGroup(newGroup);
            
            // Update local collection with server response
            if (response && response.prompt_groups) {
                this.promptGroups = response.prompt_groups;
                // Also update prompt additions in case they changed
                if (response.prompt_additions) {
                    this.promptAdditions = {};
                    for (const addition of response.prompt_additions) {
                        this.promptAdditions[addition.name] = addition;
                    }
                }
            } else {
                // Fallback: add to local collection
                this.promptGroups.push(newGroup);
            }
            
            // Refresh the groups list
            this.populateGroupsList();
            
            // Select the new group
            this.selectGroup(newGroup.id);
            
            this.updateStatus(`Created "${name}" successfully`, "success");
        } catch (error) {
            this.updateStatus("Failed to create prompt group", "error");
            console.error("Error creating prompt group:", error);
        }
    }
    
    async deleteSelectedGroup() {
        if (this.selectedGroupId === null) {
            this.updateStatus("No group selected", "error");
            return;
        }
        
        const group = this.promptGroups.find(g => g.id === this.selectedGroupId);
        if (!group) {
            this.updateStatus("Selected group not found", "error");
            return;
        }
        
        if (app.extensionManager && app.extensionManager.dialog && app.extensionManager.dialog.confirm) {
            const confirmed = await app.extensionManager.dialog.confirm({
                title: "Confirm Delete",
                message: `Are you sure you want to delete group "${group.name}"?`,
                type: "delete"
            });
            
            if (!confirmed) {
                return;
            }
        } else {
            const confirmed = await this.comfyConfirm(
                "Confirm Delete",
                `Are you sure you want to delete group "${group.name}"?`,
                "Delete",
                "Cancel"
            );
            
            if (!confirmed) {
                return;
            }
        }
        
        try {
            this.updateStatus("Deleting prompt group...", "info");
            const response = await ApiOperations.deletePromptGroup(this.selectedGroupId);
            
            // Update local collection with server response
            if (response && response.prompt_groups) {
                this.promptGroups = response.prompt_groups;
                // Also update prompt additions in case they changed
                if (response.prompt_additions) {
                    this.promptAdditions = {};
                    for (const addition of response.prompt_additions) {
                        this.promptAdditions[addition.name] = addition;
                    }
                }
            } else {
                // Fallback: remove from local collection
                this.promptGroups = this.promptGroups.filter(g => g.id !== this.selectedGroupId);
            }
            
            // Clear selection and hide edit frame
            this.selectedGroupId = null;
            this.groupEditFrame.style.display = "none";
            this.deleteGroupButton.disabled = true;
            
            // Refresh the groups list and select "(none)"
            this.populateGroupsList();
            this.selectGroup(null);
            
            this.updateStatus(`Deleted "${group.name}" successfully`, "success");
        } catch (error) {
            this.updateStatus("Failed to delete prompt group", "error");
            console.error("Error deleting prompt group:", error);
        }
    }
    
    async saveCurrentGroup() {
        if (this.selectedGroupId === null) {
            this.updateStatus("No group selected", "error");
            return;
        }
        
        const name = this.groupNameInput.value.trim();
        const triggerWordsText = this.groupTriggerWordsInput.value.trim();
        const triggerWords = triggerWordsText ? triggerWordsText.split(",").map(w => w.trim()).filter(w => w) : [];
        
        if (!name) {
            this.updateStatus("Group name cannot be empty", "error");
            return;
        }
        
        // Check if name already exists (but allow saving the same name)
        const existingGroup = this.promptGroups.find(g => g.name === name && g.id !== this.selectedGroupId);
        if (existingGroup) {
            this.updateStatus(`Group name "${name}" already exists`, "error");
            return;
        }
        
        const groupIndex = this.promptGroups.findIndex(g => g.id === this.selectedGroupId);
        if (groupIndex === -1) {
            this.updateStatus("Selected group not found", "error");
            return;
        }
        
        try {
            this.updateStatus("Saving prompt group...", "info");
            
            const updatedGroup = {
                ...this.promptGroups[groupIndex],
                name: name,
                trigger_words: triggerWords
            };
            
            const response = await ApiOperations.writePromptGroup(updatedGroup);
            
            // Update local collection with server response
            if (response && response.prompt_groups) {
                this.promptGroups = response.prompt_groups;
                // Also update prompt additions in case they changed
                if (response.prompt_additions) {
                    this.promptAdditions = {};
                    for (const addition of response.prompt_additions) {
                        this.promptAdditions[addition.name] = addition;
                    }
                }
            } else {
                // Fallback: update local collection
                this.promptGroups[groupIndex] = updatedGroup;
            }
            
            // Update selected group reference
            this.selectedGroup = { ...updatedGroup };
            
            // Refresh the groups list
            this.populateGroupsList();
            
            // Reselect the group to maintain selection
            this.selectGroup(this.selectedGroupId);
            
            this.updateStatus(`Saved "${name}" successfully`, "success");
        } catch (error) {
            this.updateStatus("Failed to save prompt group", "error");
            console.error("Error saving prompt group:", error);
        }
    }
    
    async saveCurrentGroupAndClear() {
        // Save first
        try {
            await this.saveCurrentGroup();
        } catch (error) {
            console.error("Error in saveCurrentGroup:", error);
            this.updateStatus("Failed to save group", "error");
            return;
        }
        
        // Then clear selection by setting back to "(none)" and hide fields
        this.selectedGroupId = null;
        this.selectedGroup = null;
        this.groupNameInput.value = "";
        this.groupTriggerWordsInput.value = "";
        
        // Hide the group edit frame
        this.groupEditFrame.style.display = "none";
        
        // Clear the list selection visually and select "(none)"
        const listItems = this.groupsList.querySelectorAll('div');
        listItems.forEach(item => {
            if (item.textContent === "(none)") {
                item.classList.add("selected");
                item.style.backgroundColor = "#007bff";
                item.style.borderColor = "#0056b3";
                item.style.color = "white";
            } else {
                item.classList.remove("selected");
                item.style.backgroundColor = "transparent";
                item.style.borderColor = "transparent";
                item.style.color = "";
            }
        });
        
        // Disable buttons
        this.saveGroupButton.disabled = true;
        this.revertGroupButton.disabled = true;
        this.renameGroupButton.disabled = true;
        this.deleteGroupButton.disabled = true;
        
        // Clear additions list since no group is selected
        this.populateAdditionsList();
        
        this.updateStatus("Group saved and selection cleared", "success");
    }
    
    cancelGroupSelection() {
        // Clear selection by setting back to "(none)" without saving any changes
        this.selectedGroupId = null;
        this.selectedGroup = null;
        this.groupNameInput.value = "";
        this.groupTriggerWordsInput.value = "";
        
        // Hide the group edit frame
        this.groupEditFrame.style.display = "none";
        
        // Clear the list selection visually and select "(none)"
        const listItems = this.groupsList.querySelectorAll('div');
        listItems.forEach(item => {
            if (item.textContent === "(none)") {
                item.classList.add("selected");
                item.style.backgroundColor = "#007bff";
                item.style.borderColor = "#0056b3";
                item.style.color = "white";
            } else {
                item.classList.remove("selected");
                item.style.backgroundColor = "transparent";
                item.style.borderColor = "transparent";
                item.style.color = "";
            }
        });
        
        // Disable buttons
        this.saveGroupButton.disabled = true;
        this.revertGroupButton.disabled = true;
        this.renameGroupButton.disabled = true;
        this.deleteGroupButton.disabled = true;
        
        // Clear additions list since no group is selected
        this.populateAdditionsList();
        
        this.updateStatus("Group selection cancelled", "info");
    }
    
    async renameSelectedGroup() {
        if (!this.selectedGroup || this.selectedGroupId === null) {
            this.updateStatus("No group selected to rename", "error");
            return;
        }
        
        const currentName = this.selectedGroup.name;
        const newName = await this.promptForName("Rename Prompt Group", `Rename "${currentName}" to:`, currentName);
        
        if (!newName) {
            this.updateStatus("Group rename cancelled", "info");
            return;
        }
        
        if (newName === currentName) {
            this.updateStatus("Group name unchanged", "info");
            return;
        }
        
        // Check if name already exists
        const existingGroup = this.promptGroups.find(g => g.name === newName && g.id !== this.selectedGroupId);
        if (existingGroup) {
            this.updateStatus(`Group name "${newName}" already exists`, "error");
            return;
        }
        
        try {
            this.updateStatus("Renaming prompt group...", "info");
            
            const updatedGroup = {
                ...this.selectedGroup,
                name: newName
            };
            
            const response = await ApiOperations.writePromptGroup(updatedGroup);
            
            // Update local collection with server response
            if (response && response.prompt_groups) {
                this.promptGroups = response.prompt_groups;
                if (response.prompt_additions) {
                    this.promptAdditions = {};
                    for (const addition of response.prompt_additions) {
                        this.promptAdditions[addition.name] = addition;
                    }
                }
            }
            
            // Update UI
            this.groupNameInput.value = newName;
            this.selectedGroup = { ...updatedGroup };
            this.populateGroupsList();
            this.selectGroup(this.selectedGroupId);
            
            this.updateStatus(`Renamed group to "${newName}" successfully`, "success");
        } catch (error) {
            this.updateStatus("Failed to rename prompt group", "error");
            console.error("Error renaming prompt group:", error);
        }
    }
    
    async renameSelectedAddition() {
        if (!this.selectedAdditionName) {
            this.updateStatus("No addition selected to rename", "error");
            return;
        }
        
        const currentName = this.selectedAdditionName;
        const newName = await this.promptForName("Rename Prompt Addition", `Rename "${currentName}" to:`, currentName);
        
        if (!newName) {
            this.updateStatus("Addition rename cancelled", "info");
            return;
        }
        
        if (newName === currentName) {
            this.updateStatus("Addition name unchanged", "info");
            return;
        }
        
        // Check if name already exists
        if (this.promptAdditions[newName]) {
            this.updateStatus(`Addition name "${newName}" already exists`, "error");
            return;
        }
        
        try {
            this.updateStatus("Renaming prompt addition...", "info");
            
            const currentAddition = this.promptAdditions[currentName];
            const updatedAddition = {
                ...currentAddition,
                name: newName
            };
            
            // First create the new addition
            await ApiOperations.writePromptAddition(updatedAddition);
            
            // Then delete the old addition
            await ApiOperations.deletePromptAddition(currentName);
            
            // Get fresh data from server
            const freshData = await ApiOperations.getPromptAdditions();
            if (freshData && freshData.prompt_additions) {
                this.promptAdditions = {};
                for (const addition of freshData.prompt_additions) {
                    this.promptAdditions[addition.name] = addition;
                }
                this.promptGroups = freshData.prompt_groups || [];
            }
            
            // Update UI
            this.selectedAdditionName = newName;
            this.originalAdditionData.name = newName;
            this.populateAdditionsList();
            this.selectAddition(newName);
            
            // Update the node's selected addition if we have a node reference
            if (this.node && this.node.promptAdditionNameWidget) {
                this.node.promptAdditionNameWidget.value = newName;
                if (this.node.promptAdditionNameWidget.callback) {
                    this.node.promptAdditionNameWidget.callback();
                }
            }
            
            this.updateStatus(`Renamed addition to "${newName}" successfully`, "success");
        } catch (error) {
            this.updateStatus("Failed to rename prompt addition", "error");
            console.error("Error renaming prompt addition:", error);
        }
    }
    
    getNextGroupId() {
        const maxId = this.promptGroups.reduce((max, group) => Math.max(max, group.id || 0), 0);
        return maxId + 1;
    }

    async quickSave(config) {
        try {
            // Check if addition with this name already exists
            const existingAddition = this.promptAdditions[config.name];
            
            let confirmOverwrite = true;
            if (existingAddition) {
                confirmOverwrite = await this.comfyConfirm(
                    "Overwrite Existing",
                    `A prompt addition named "${config.name}" already exists. Do you want to overwrite it?`,
                    "Overwrite",
                    "Cancel"
                );
            }
            
            if (!confirmOverwrite) return;
            
            // Create the prompt addition data
            const promptAdditionData = {
                name: config.name,
                trigger_words: config.trigger_words || "",
                positive_prompt_addition_text: config.positive_prompt_addition_text || "",
                negative_prompt_addition_text: config.negative_prompt_addition_text || "",
                id: existingAddition ? existingAddition.id : undefined
            };
            
            // Save via API
            const response = await ApiOperations.writePromptAddition(promptAdditionData);
            
            if (response && response.success) {
                // Update local data
                this.promptAdditions[config.name] = promptAdditionData;
                
                // Update the node's prompt data if it exists
                if (this.node) {
                    this.node.updatePromptData(this.node, response.data);
                }
                
                // Show success message
                this.comfyNotify(`Prompt addition "${config.name}" saved successfully!`, "success");
                
            } else {
                const errorMessage = response?.message || "Failed to save prompt addition - no response from server";
                throw new Error(errorMessage);
            }
            
        } catch (error) {
            console.error("Error in quickSave:", error);
            this.comfyNotify("Error saving prompt addition: " + error.message, "error");
        }
    }

    show() {
        super.show(this.content);
        
        // Save and Save As buttons should always be enabled (they can create new additions)
        this.saveButton.disabled = false;
        this.saveAsButton.disabled = false;
        
        // OK button should always be enabled (can close dialog without selection)
        this.okButton.disabled = false;
        
        // Auto-select the current addition if it exists
        if (this.currentAdditionName && this.promptAdditions[this.currentAdditionName]) {
            this.selectAddition(this.currentAdditionName);
        }
        
        this.positiveTextarea.focus();
    }
}

export { PromptAdditionManager };