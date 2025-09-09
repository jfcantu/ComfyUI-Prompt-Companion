import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import { ApiOperations } from "./api-operations.js";
import { PromptAdditionManager } from "./promptAdditionManager.js";


app.registerExtension({
    name: "ComfyUI.Prompt.Companion",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        // Add right-click functionality for all Prompt Companion nodes
        const promptCompanionNodes = [
            "PromptCompanion", 
            "PromptAdditionInput", 
            "PromptCompanionSingleAddition", 
            "PromptCompanionPromptGroup", 
            "PromptCompanionAutoselectGroups", 
            "PromptCompanionStringsToAddition", 
            "PromptCompanionAdditionToStrings"
        ];

        if (promptCompanionNodes.includes(nodeType.comfyClass)) {
            // Add the right-click menu option for all Prompt Companion nodes
            nodeType.prototype.getExtraMenuOptions = function(_, options) {
                try {
                    options.push({
                        content: "Edit Prompt Additions",
                        callback: () => {
                            try {
                                // For PromptCompanion, try to get current selection
                                let currentAdditionName = null;
                                if (this.promptAdditionNameWidget?.value) {
                                    currentAdditionName = this.promptAdditionNameWidget.value;
                                }
                                
                                const promptData = {
                                    prompt_additions: Object.values(this.promptAdditions || {}),
                                    prompt_groups: this.promptGroups || []
                                };
                                const manager = new PromptAdditionManager(promptData, this, currentAdditionName);
                                manager.show();
                            } catch (error) {
                                console.error("Error creating/showing PromptAdditionManager:", error);
                            }
                        }
                    });
                } catch (error) {
                    console.error("Error in getExtraMenuOptions:", error);
                }
                return options;
            };

            // Add cleanup method for proper memory management for all Prompt Companion nodes
            const originalOnRemoved = nodeType.prototype.onRemoved;
            
            nodeType.prototype.onRemoved = function() {
                // Clean up event listeners to prevent memory leaks
                if (this.eventListener) {
                    api.removeEventListener("prompt-companion.addition-list", this.eventListener);
                    this.eventListener = null;
                }
                
                // Clean up any other references
                this.promptAdditions = null;
                this.promptAdditionNames = null;
                this.promptGroups = null;
                
                // Call original cleanup if it exists
                if (originalOnRemoved) {
                    originalOnRemoved.call(this);
                }
            };
        }

        if (nodeType.comfyClass == "PromptCompanion") {
            
            nodeType.prototype.updatePromptData = function (node, promptAdditionsData) {
                // Handle both old format (array) and new format (object with prompt_additions)
                const promptAdditions = Array.isArray(promptAdditionsData) ? 
                    promptAdditionsData : 
                    (promptAdditionsData.prompt_additions || []);
                
                let newPromptAdditionsObject = {};
                for (const promptAddition of promptAdditions) {
                    newPromptAdditionsObject[promptAddition.name] = promptAddition;
                }

                this.promptAdditions = newPromptAdditionsObject;
                this.promptAdditionNames = Object.keys(this.promptAdditions);
                
                // Update prompt groups
                this.promptGroups = promptAdditionsData.prompt_groups || [];
                
                // Update widget options
                this.refreshWidgetOptions(node);
            };
            
            nodeType.prototype.refreshWidgetOptions = function (node) {
                // Update prompt addition names
                if (node.promptAdditionNameWidget) {
                    const additionNames = Object.keys(this.promptAdditions);
                    node.promptAdditionNameWidget.options.values = additionNames.length > 0 ? additionNames : [""];
                }
                
                // Update prompt group names
                if (node.promptAdditionGroupWidget) {
                    const groupNames = this.promptGroups.map(g => g.name);
                    node.promptAdditionGroupWidget.options.values = groupNames.length > 0 ? groupNames : [""];
                }
                
                // Handle widget visibility based on addition_type
                this.updateWidgetVisibility(node);
            };
            
            nodeType.prototype.updateWidgetVisibility = function (node) {
                if (!node.additionTypeWidget) return;
                
                const additionType = node.additionTypeWidget.value;
                const isIndividual = additionType === "Individual";
                const groupMode = node.promptGroupModeWidget?.value || "Manual";
                
                // Enable/disable prompt_group_mode based on addition_type
                if (node.promptGroupModeWidget) {
                    if (isIndividual) {
                        node.promptGroupModeWidget.disabled = true;
                        if (node.promptGroupModeWidget.inputEl) {
                            node.promptGroupModeWidget.inputEl.style.opacity = "0.5";
                            node.promptGroupModeWidget.inputEl.style.pointerEvents = "none";
                        }
                    } else {
                        node.promptGroupModeWidget.disabled = false;
                        if (node.promptGroupModeWidget.inputEl) {
                            node.promptGroupModeWidget.inputEl.style.opacity = "1";
                            node.promptGroupModeWidget.inputEl.style.pointerEvents = "auto";
                        }
                    }
                }
                
                // Enable/disable prompt_addition_name and prompt_addition_group based on mode
                if (node.promptAdditionNameWidget) {
                    if (isIndividual) {
                        node.promptAdditionNameWidget.disabled = false;
                        if (node.promptAdditionNameWidget.inputEl) {
                            node.promptAdditionNameWidget.inputEl.style.opacity = "1";
                            node.promptAdditionNameWidget.inputEl.style.pointerEvents = "auto";
                        }
                    } else {
                        node.promptAdditionNameWidget.disabled = true;
                        if (node.promptAdditionNameWidget.inputEl) {
                            node.promptAdditionNameWidget.inputEl.style.opacity = "0.5";
                            node.promptAdditionNameWidget.inputEl.style.pointerEvents = "none";
                        }
                    }
                }
                
                if (node.promptAdditionGroupWidget) {
                    if (isIndividual || groupMode === "Automatic (Trigger Words)") {
                        node.promptAdditionGroupWidget.disabled = true;
                        if (node.promptAdditionGroupWidget.inputEl) {
                            node.promptAdditionGroupWidget.inputEl.style.opacity = "0.5";
                            node.promptAdditionGroupWidget.inputEl.style.pointerEvents = "none";
                        }
                    } else {
                        node.promptAdditionGroupWidget.disabled = false;
                        if (node.promptAdditionGroupWidget.inputEl) {
                            node.promptAdditionGroupWidget.inputEl.style.opacity = "1";
                            node.promptAdditionGroupWidget.inputEl.style.pointerEvents = "auto";
                        }
                    }
                }
                
                // Update addition textbox behavior
                this.updateAdditionTextboxes(node, additionType, groupMode);
                
                // Keep prompt textboxes visible at all times
                // (Removed connection-based hiding as requested)
                
                // No need to resize - just enable/disable widgets
            };
            
            nodeType.prototype.updateAdditionTextboxes = function (node, additionType, groupMode) {
                if (!node.positiveAdditionWidget || !node.negativeAdditionWidget) return;
                
                if (additionType === "Individual") {
                    // Individual mode - textboxes are editable
                    if (node.positiveAdditionWidget.inputEl) {
                        node.positiveAdditionWidget.inputEl.readOnly = false;
                        node.positiveAdditionWidget.inputEl.style.backgroundColor = "";
                        node.positiveAdditionWidget.inputEl.style.color = "";
                    }
                    if (node.negativeAdditionWidget.inputEl) {
                        node.negativeAdditionWidget.inputEl.readOnly = false;
                        node.negativeAdditionWidget.inputEl.style.backgroundColor = "";
                        node.negativeAdditionWidget.inputEl.style.color = "";
                    }
                    
                    // Load selected addition data
                    this.loadSelectedAdditionData(node);
                    
                } else if (additionType === "Group") {
                    // Group mode - textboxes are read-only and show computed values
                    if (node.positiveAdditionWidget.inputEl) {
                        node.positiveAdditionWidget.inputEl.readOnly = true;
                        node.positiveAdditionWidget.inputEl.style.setProperty('background-color', '#2a2a2a', 'important');
                        node.positiveAdditionWidget.inputEl.style.setProperty('color', '#999', 'important');
                    }
                    if (node.negativeAdditionWidget.inputEl) {
                        node.negativeAdditionWidget.inputEl.readOnly = true;
                        node.negativeAdditionWidget.inputEl.style.setProperty('background-color', '#2a2a2a', 'important');
                        node.negativeAdditionWidget.inputEl.style.setProperty('color', '#999', 'important');
                    }
                    
                    // Force style update after a short delay to ensure it takes effect
                    setTimeout(() => {
                        if (node.positiveAdditionWidget.inputEl) {
                            node.positiveAdditionWidget.inputEl.style.setProperty('background-color', '#2a2a2a', 'important');
                            node.positiveAdditionWidget.inputEl.style.setProperty('color', '#999', 'important');
                        }
                        if (node.negativeAdditionWidget.inputEl) {
                            node.negativeAdditionWidget.inputEl.style.setProperty('background-color', '#2a2a2a', 'important');
                            node.negativeAdditionWidget.inputEl.style.setProperty('color', '#999', 'important');
                        }
                    }, 100);
                    
                    // Load group data based on mode
                    if (groupMode === "Manual") {
                        this.loadGroupAdditionData(node);
                    } else {
                        // Automatic mode - compute based on ckpt_name trigger words
                        this.loadAutomaticGroupData(node);
                    }
                }
            };
            
            nodeType.prototype.loadAutomaticGroupData = function (node) {
                // Clear first
                if (node.positiveAdditionWidget) node.positiveAdditionWidget.value = "";
                if (node.negativeAdditionWidget) node.negativeAdditionWidget.value = "";
                
                // Get ckpt_name to check trigger words against
                const ckptName = node.widgets?.find(w => w.name === "ckpt_name")?.value || "";
                if (!ckptName) return;
                
                const positiveAdditions = [];
                const negativeAdditions = [];
                
                // Check all groups for trigger word matches
                for (const group of this.promptGroups) {
                    // Check if any trigger words match in ckpt_name
                    let triggerMatch = false;
                    for (const triggerWord of (group.trigger_words || [])) {
                        if (triggerWord && ckptName.toLowerCase().includes(triggerWord.toLowerCase())) {
                            triggerMatch = true;
                            break;
                        }
                    }
                    
                    if (triggerMatch && group.additions) {
                        // Get all additions in this group
                        for (const additionRef of group.additions) {
                            const additionId = additionRef.addition_id;
                            const addition = Object.values(this.promptAdditions).find(a => a.id === additionId);
                            
                            if (addition) {
                                if (addition.positive_prompt_addition_text) {
                                    positiveAdditions.push(addition.positive_prompt_addition_text);
                                }
                                if (addition.negative_prompt_addition_text) {
                                    negativeAdditions.push(addition.negative_prompt_addition_text);
                                }
                            }
                        }
                    }
                }
                
                // Set computed values
                if (node.positiveAdditionWidget) {
                    node.positiveAdditionWidget.value = positiveAdditions.join(", ");
                }
                if (node.negativeAdditionWidget) {
                    node.negativeAdditionWidget.value = negativeAdditions.join(", ");
                }
            };
            
            
            nodeType.prototype.updatePromptTextboxVisibility = function (node) {
                // Check if positive_prompt input is connected
                const positivePromptConnected = node.inputs && node.inputs.some(input => 
                    input.name === "positive_prompt" && input.link !== null
                );
                
                // Check if negative_prompt input is connected
                const negativePromptConnected = node.inputs && node.inputs.some(input => 
                    input.name === "negative_prompt" && input.link !== null
                );
                
                // Show textbox if input is NOT connected (opposite of connection state)
                if (node.positivePromptWidget) {
                    if (!positivePromptConnected) {
                        node.positivePromptWidget.type = node.positivePromptWidget.origType;
                        node.positivePromptWidget.computeSize = node.positivePromptWidget.origComputeSize;
                    } else {
                        node.positivePromptWidget.type = "converted-widget";
                        node.positivePromptWidget.computeSize = () => [0, -4];
                    }
                }
                if (node.negativePromptWidget) {
                    if (!negativePromptConnected) {
                        node.negativePromptWidget.type = node.negativePromptWidget.origType;
                        node.negativePromptWidget.computeSize = node.negativePromptWidget.origComputeSize;
                    } else {
                        node.negativePromptWidget.type = "converted-widget";
                        node.negativePromptWidget.computeSize = () => [0, -4];
                    }
                }
            };
            
            nodeType.prototype.loadSelectedAdditionData = function (node) {
                if (!node.promptAdditionNameWidget || !node.promptAdditionNameWidget.value) {
                    if (node.positiveAdditionWidget) node.positiveAdditionWidget.value = "";
                    if (node.negativeAdditionWidget) node.negativeAdditionWidget.value = "";
                    return;
                }
                
                const additionName = node.promptAdditionNameWidget.value;
                const addition = this.promptAdditions[additionName];
                
                if (addition) {
                    if (node.positiveAdditionWidget) {
                        node.positiveAdditionWidget.value = addition.positive_prompt_addition_text || "";
                    }
                    if (node.negativeAdditionWidget) {
                        node.negativeAdditionWidget.value = addition.negative_prompt_addition_text || "";
                    }
                }
            };
            
            nodeType.prototype.loadGroupAdditionData = function (node) {
                if (!node.promptAdditionGroupWidget || !node.promptAdditionGroupWidget.value) {
                    if (node.positiveAdditionWidget) node.positiveAdditionWidget.value = "";
                    if (node.negativeAdditionWidget) node.negativeAdditionWidget.value = "";
                    return;
                }
                
                const groupName = node.promptAdditionGroupWidget.value;
                const group = this.promptGroups.find(g => g.name === groupName);
                
                if (group && group.additions) {
                    const positiveAdditions = [];
                    const negativeAdditions = [];
                    
                    // Get all additions in this group
                    for (const additionRef of group.additions) {
                        const additionId = additionRef.addition_id;
                        const addition = Object.values(this.promptAdditions).find(a => a.id === additionId);
                        
                        if (addition) {
                            if (addition.positive_prompt_addition_text) {
                                positiveAdditions.push(addition.positive_prompt_addition_text);
                            }
                            if (addition.negative_prompt_addition_text) {
                                negativeAdditions.push(addition.negative_prompt_addition_text);
                            }
                        }
                    }
                    
                    if (node.positiveAdditionWidget) {
                        node.positiveAdditionWidget.value = positiveAdditions.join(", ");
                    }
                    if (node.negativeAdditionWidget) {
                        node.negativeAdditionWidget.value = negativeAdditions.join(", ");
                    }
                }
            };
            
            nodeType.prototype.saveCurrentConfiguration = function() {
                try {
                    // Get current addition text values (not prompt text)
                    const positiveAdditionText = this.positiveAdditionWidget?.value || "";
                    const negativeAdditionText = this.negativeAdditionWidget?.value || "";
                    
                    if (!positiveAdditionText && !negativeAdditionText) {
                        // Use ComfyUI-style notification instead of alert
                        if (app.ui && app.ui.dialog && app.ui.dialog.show) {
                            app.ui.dialog.show("No prompt additions to save. Please add some text to the positive or negative addition fields.");
                        } else {
                            console.warn("No prompt additions to save. Please add some text to the positive or negative addition fields.");
                        }
                        return;
                    }
                    
                    // Check if we have a selected addition name to save to
                    const currentAdditionName = this.promptAdditionNameWidget?.value;
                    
                    if (currentAdditionName && currentAdditionName.trim()) {
                        // Use the existing name - this is a regular "Save" operation
                        const config = {
                            name: currentAdditionName.trim(),
                            positive_prompt_addition_text: positiveAdditionText,
                            negative_prompt_addition_text: negativeAdditionText,
                            trigger_words: ""
                        };
                        
                        // Create a new prompt addition
                        const promptData = {
                            prompt_additions: Object.values(this.promptAdditions || {}),
                            prompt_groups: this.promptGroups || []
                        };
                        
                        const manager = new PromptAdditionManager(promptData, this);
                        manager.quickSave(config);
                        
                    } else {
                        // No addition selected - prompt for a name (like "Save As")
                        const suggestedName = positiveAdditionText ? 
                            positiveAdditionText.trim().split(/\s+/).slice(0, 3).join(" ") : 
                            "New Addition";
                        
                        const showNamePrompt = async () => {
                            return new Promise((resolve) => {
                                if (app.ui && app.ui.dialog && app.ui.dialog.prompt) {
                                    app.ui.dialog.prompt("Enter a name for this prompt addition:", suggestedName)
                                        .then(name => resolve(name))
                                        .catch(() => resolve(null));
                                } else {
                                    // Fallback to browser prompt if ComfyUI dialog not available
                                    const name = prompt("Enter a name for this prompt addition:", suggestedName);
                                    resolve(name);
                                }
                            });
                        };
                        
                        showNamePrompt().then(name => {
                            if (!name) return;
                            
                            const config = {
                                name: name,
                                positive_prompt_addition_text: positiveAdditionText,
                                negative_prompt_addition_text: negativeAdditionText,
                                trigger_words: ""
                            };
                            
                            // Create a new prompt addition
                            const promptData = {
                                prompt_additions: Object.values(this.promptAdditions || {}),
                                prompt_groups: this.promptGroups || []
                            };
                            
                            const manager = new PromptAdditionManager(promptData, this);
                            manager.quickSave(config);
                        });
                    }
                    
                } catch (error) {
                    console.error("Error saving configuration:", error);
                    // Use ComfyUI-style notification instead of alert
                    if (app.ui && app.ui.dialog && app.ui.dialog.show) {
                        app.ui.dialog.show("Error saving configuration: " + error.message);
                    } else {
                        console.error("Error saving configuration: " + error.message);
                    }
                }
            };
            
            nodeType.prototype.saveAsConfiguration = function() {
                try {
                    // Get current addition text values (not prompt text)
                    const config = {
                        positive_prompt_addition_text: this.positiveAdditionWidget?.value || "",
                        negative_prompt_addition_text: this.negativeAdditionWidget?.value || "",
                        trigger_words: ""
                    };
                    
                    if (!config.positive_prompt_addition_text && !config.negative_prompt_addition_text) {
                        // Use ComfyUI-style notification instead of alert
                        if (app.ui && app.ui.dialog && app.ui.dialog.show) {
                            app.ui.dialog.show("No prompt additions to save. Please add some text to the positive or negative addition fields.");
                        } else {
                            console.warn("No prompt additions to save. Please add some text to the positive or negative addition fields.");
                        }
                        return;
                    }
                    
                    // Use ComfyUI-style prompt instead of browser prompt
                    const showNamePrompt = async () => {
                        return new Promise((resolve) => {
                            if (app.ui && app.ui.dialog && app.ui.dialog.prompt) {
                                app.ui.dialog.prompt("Enter a name for this prompt addition:", "New Addition")
                                    .then(name => resolve(name))
                                    .catch(() => resolve(null));
                            } else {
                                // Fallback to browser prompt if ComfyUI dialog not available
                                const name = prompt("Enter a name for this prompt addition:", "New Addition");
                                resolve(name);
                            }
                        });
                    };
                    
                    showNamePrompt().then(name => {
                        if (!name) return;
                        
                        config.name = name;
                        
                        // Create a new prompt addition
                        const promptData = {
                            prompt_additions: Object.values(this.promptAdditions || {}),
                            prompt_groups: this.promptGroups || []
                        };
                        
                        const manager = new PromptAdditionManager(promptData, this);
                        manager.quickSave(config);
                    });
                    
                } catch (error) {
                    console.error("Error saving configuration:", error);
                    // Use ComfyUI-style notification instead of alert
                    if (app.ui && app.ui.dialog && app.ui.dialog.show) {
                        app.ui.dialog.show("Error saving configuration: " + error.message);
                    } else {
                        console.error("Error saving configuration: " + error.message);
                    }
                }
            };

        }
    },
    async nodeCreated(node) {
        // Initialize prompt data for all Prompt Companion nodes
        const promptCompanionNodes = [
            "PromptCompanion", 
            "PromptAdditionInput", 
            "PromptCompanionSingleAddition", 
            "PromptCompanionPromptGroup", 
            "PromptCompanionAutoselectGroups", 
            "PromptCompanionStringsToAddition", 
            "PromptCompanionAdditionToStrings"
        ];

        if (promptCompanionNodes.includes(node.comfyClass)) {
            // Initialize prompt data for all nodes
            node.promptAdditions = {};
            node.promptAdditionNames = {};
            node.promptGroups = [];

            // Load prompt data
            const promptAdditions = await ApiOperations.getPromptAdditions();
            if (node.updatePromptData) {
                node.updatePromptData(node, promptAdditions);
            } else {
                // For nodes without updatePromptData method, set data directly
                const promptAdditionsData = Array.isArray(promptAdditions) ? 
                    promptAdditions : 
                    (promptAdditions.prompt_additions || []);
                
                let newPromptAdditionsObject = {};
                for (const promptAddition of promptAdditionsData) {
                    newPromptAdditionsObject[promptAddition.name] = promptAddition;
                }

                node.promptAdditions = newPromptAdditionsObject;
                node.promptAdditionNames = Object.keys(newPromptAdditionsObject);
                node.promptGroups = promptAdditions.prompt_groups || [];
            }

            // Set up event listener for updates
            const eventListener = (event) => {
                if (node.updatePromptData) {
                    node.updatePromptData(node, event.detail);
                } else {
                    // For nodes without updatePromptData method, update data directly
                    const promptAdditionsData = Array.isArray(event.detail) ? 
                        event.detail : 
                        (event.detail.prompt_additions || []);
                    
                    let newPromptAdditionsObject = {};
                    for (const promptAddition of promptAdditionsData) {
                        newPromptAdditionsObject[promptAddition.name] = promptAddition;
                    }

                    node.promptAdditions = newPromptAdditionsObject;
                    node.promptAdditionNames = Object.keys(newPromptAdditionsObject);
                    node.promptGroups = event.detail.prompt_groups || [];
                }
            };
            
            api.addEventListener("prompt-companion.addition-list", eventListener);
            
            // Store the event listener for cleanup
            node.eventListener = eventListener;
        }

        if (node.comfyClass == "PromptCompanion") {

            // Get widget references
            node.ckptNameWidget = node.widgets?.find((w) => w.name === "ckpt_name");
            node.additionTypeWidget = node.widgets?.find((w) => w.name === "addition_type");
            node.promptGroupModeWidget = node.widgets?.find((w) => w.name === "prompt_group_mode");
            node.promptAdditionNameWidget = node.widgets?.find((w) => w.name === "prompt_addition_name");
            node.promptAdditionGroupWidget = node.widgets?.find((w) => w.name === "prompt_addition_group");
            node.positiveAdditionWidget = node.widgets?.find((w) => w.name === "positive_addition");
            node.negativeAdditionWidget = node.widgets?.find((w) => w.name === "negative_addition");
            node.positivePromptWidget = node.widgets?.find((w) => w.name === "positive_prompt");
            node.negativePromptWidget = node.widgets?.find((w) => w.name === "negative_prompt");

            // Store original types and computeSize functions for dynamic visibility
            if (node.promptAdditionNameWidget) {
                node.promptAdditionNameWidget.origType = node.promptAdditionNameWidget.type;
                node.promptAdditionNameWidget.origComputeSize = node.promptAdditionNameWidget.computeSize;
            }
            if (node.promptAdditionGroupWidget) {
                node.promptAdditionGroupWidget.origType = node.promptAdditionGroupWidget.type;
                node.promptAdditionGroupWidget.origComputeSize = node.promptAdditionGroupWidget.computeSize;
            }
            if (node.promptGroupModeWidget) {
                node.promptGroupModeWidget.origType = node.promptGroupModeWidget.type;
                node.promptGroupModeWidget.origComputeSize = node.promptGroupModeWidget.computeSize;
            }
            if (node.positivePromptWidget) {
                node.positivePromptWidget.origType = node.positivePromptWidget.type;
                node.positivePromptWidget.origComputeSize = node.positivePromptWidget.computeSize;
            }
            if (node.negativePromptWidget) {
                node.negativePromptWidget.origType = node.negativePromptWidget.type;
                node.negativePromptWidget.origComputeSize = node.negativePromptWidget.computeSize;
            }

            // Set up callbacks with proper context binding
            if (node.ckptNameWidget) {
                const originalCkptCallback = node.ckptNameWidget.callback;
                node.ckptNameWidget.callback = function() {
                    // Call original callback if it exists
                    if (originalCkptCallback) {
                        originalCkptCallback.apply(this, arguments);
                    }
                    // Trigger automatic group data update if in Group mode with Automatic
                    if (node.additionTypeWidget?.value === "Group" && node.promptGroupModeWidget?.value === "Automatic (Trigger Words)") {
                        node.loadAutomaticGroupData(node);
                    }
                };
            }
            
            if (node.additionTypeWidget) {
                const originalTypeCallback = node.additionTypeWidget.callback;
                node.additionTypeWidget.callback = function() {
                    // Call original callback if it exists
                    if (originalTypeCallback) {
                        originalTypeCallback.apply(this, arguments);
                    }
                    node.updateWidgetVisibility(node);
                };
            }
            
            if (node.promptGroupModeWidget) {
                const originalGroupModeCallback = node.promptGroupModeWidget.callback;
                node.promptGroupModeWidget.callback = function() {
                    // Call original callback if it exists
                    if (originalGroupModeCallback) {
                        originalGroupModeCallback.apply(this, arguments);
                    }
                    node.updateWidgetVisibility(node);
                };
            }
            
            if (node.promptAdditionNameWidget) {
                const originalNameCallback = node.promptAdditionNameWidget.callback;
                node.promptAdditionNameWidget.callback = function() {
                    // Call original callback if it exists
                    if (originalNameCallback) {
                        originalNameCallback.apply(this, arguments);
                    }
                    if (node.additionTypeWidget?.value === "Individual") {
                        node.loadSelectedAdditionData(node);
                    }
                };
            }
            
            if (node.promptAdditionGroupWidget) {
                const originalGroupCallback = node.promptAdditionGroupWidget.callback;
                node.promptAdditionGroupWidget.callback = function() {
                    // Call original callback if it exists
                    if (originalGroupCallback) {
                        originalGroupCallback.apply(this, arguments);
                    }
                    if (node.additionTypeWidget?.value === "Group" && node.promptGroupModeWidget?.value === "Manual") {
                        node.loadGroupAdditionData(node);
                    }
                };
            }

            // Add Save and Save As buttons
            node.addWidget("button", "Save", "save", () => {
                node.saveCurrentConfiguration();
            });
            
            node.addWidget("button", "Save As", "save_as", () => {
                node.saveAsConfiguration();
            });

            
            // Connection change handler removed - keeping textboxes visible at all times
            
            // Initial visibility update
            setTimeout(() => {
                node.updateWidgetVisibility(node);
            }, 100);
        }
    },
    async getCustomWidgets(app) {
        
    }
});