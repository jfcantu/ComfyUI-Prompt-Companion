/**
 * Centralized State Management for Prompt Companion
 * 
 * Provides a single source of truth for application state with:
 * - Event-driven updates
 * - Automatic persistence
 * - Change notifications
 * - Validation
 */

import { ApiOperations } from "./api-operations.js";

/**
 * @typedef {Object} PromptAddition
 * @property {number} id - Unique identifier
 * @property {string} name - Display name
 * @property {string} trigger_words - Comma-separated trigger words
 * @property {string} positive_prompt_addition_text - Positive prompt text
 * @property {string} negative_prompt_addition_text - Negative prompt text
 */

/**
 * @typedef {Object} PromptGroup
 * @property {number} id - Unique identifier
 * @property {string} name - Display name
 * @property {string[]} trigger_words - Array of trigger words
 * @property {Array} additions - Array of addition references
 */

/**
 * @typedef {Object} UIState
 * @property {string|null} selectedAddition - Currently selected addition name
 * @property {number|null} selectedGroup - Currently selected group ID
 * @property {string} currentMode - Current operation mode (Individual/Group)
 * @property {boolean} isLoading - Loading state indicator
 */

/**
 * @typedef {Object} AppData
 * @property {Object<string, PromptAddition>} additions - Map of addition name to data
 * @property {PromptGroup[]} groups - Array of prompt groups
 * @property {number} lastSync - Timestamp of last server sync
 */

export class PromptState {
    constructor() {
        /** @type {AppData} */
        this.data = {
            additions: {},
            groups: [],
            lastSync: 0
        };
        
        /** @type {UIState} */
        this.ui = {
            selectedAddition: null,
            selectedGroup: null,
            currentMode: "Individual",
            isLoading: false
        };
        
        /** @type {Set<Function>} */
        this.listeners = new Set();
        
        /** @type {Set<Function>} */
        this.errorHandlers = new Set();
        
        // Debounce timer for auto-save
        this.saveTimer = null;
        this.SAVE_DELAY = 1000; // 1 second debounce
    }
    
    /**
     * Subscribe to state changes
     * @param {Function} callback - Function to call on state changes
     * @returns {Function} Unsubscribe function
     */
    subscribe(callback) {
        this.listeners.add(callback);
        return () => this.listeners.delete(callback);
    }
    
    /**
     * Subscribe to error events
     * @param {Function} callback - Function to call on errors
     * @returns {Function} Unsubscribe function
     */
    onError(callback) {
        this.errorHandlers.add(callback);
        return () => this.errorHandlers.delete(callback);
    }
    
    /**
     * Notify all subscribers of state changes
     * @param {string} action - Action that triggered the change
     * @param {Object} payload - Additional data about the change
     */
    notify(action, payload = {}) {
        const stateSnapshot = {
            data: JSON.parse(JSON.stringify(this.data)),
            ui: { ...this.ui },
            action,
            payload,
            timestamp: Date.now()
        };
        
        this.listeners.forEach(callback => {
            try {
                callback(stateSnapshot);
            } catch (error) {
                console.error("Error in state listener:", error);
                this.notifyError("LISTENER_ERROR", error);
            }
        });
    }
    
    /**
     * Notify error handlers
     * @param {string} type - Error type
     * @param {Error} error - The error object
     */
    notifyError(type, error) {
        this.errorHandlers.forEach(handler => {
            try {
                handler({ type, error, timestamp: Date.now() });
            } catch (e) {
                console.error("Error in error handler:", e);
            }
        });
    }
    
    /**
     * Load initial data from server
     * @returns {Promise<void>}
     */
    async initialize() {
        try {
            this.setLoading(true);
            const serverData = await ApiOperations.getPromptAdditions();
            
            if (serverData) {
                this.updateFromServerData(serverData);
                this.notify("INITIALIZED", { source: "server" });
            }
        } catch (error) {
            console.error("Failed to initialize state:", error);
            this.notifyError("INIT_ERROR", error);
        } finally {
            this.setLoading(false);
        }
    }
    
    /**
     * Update state from server response data
     * @param {Object} serverData - Data from server
     */
    updateFromServerData(serverData) {
        // Handle both old and new data formats
        const additions = Array.isArray(serverData) ? 
            serverData : 
            (serverData.prompt_additions || []);
        
        // Convert array to object keyed by name
        this.data.additions = {};
        additions.forEach(addition => {
            this.data.additions[addition.name] = addition;
        });
        
        // Update groups
        this.data.groups = serverData.prompt_groups || [];
        this.data.lastSync = Date.now();
        
        this.notify("DATA_UPDATED", { source: "server" });
    }
    
    /**
     * Set loading state
     * @param {boolean} isLoading - Loading state
     */
    setLoading(isLoading) {
        if (this.ui.isLoading !== isLoading) {
            this.ui.isLoading = isLoading;
            this.notify("LOADING_CHANGED", { isLoading });
        }
    }
    
    /**
     * Select a prompt addition
     * @param {string|null} additionName - Name of addition to select
     */
    selectAddition(additionName) {
        if (this.ui.selectedAddition !== additionName) {
            const previousSelection = this.ui.selectedAddition;
            this.ui.selectedAddition = additionName;
            this.notify("ADDITION_SELECTED", { 
                current: additionName, 
                previous: previousSelection 
            });
        }
    }
    
    /**
     * Select a prompt group
     * @param {number|null} groupId - ID of group to select
     */
    selectGroup(groupId) {
        if (this.ui.selectedGroup !== groupId) {
            const previousSelection = this.ui.selectedGroup;
            this.ui.selectedGroup = groupId;
            this.notify("GROUP_SELECTED", { 
                current: groupId, 
                previous: previousSelection 
            });
        }
    }
    
    /**
     * Set current operation mode
     * @param {string} mode - Mode to set (Individual/Group)
     */
    setMode(mode) {
        if (this.ui.currentMode !== mode) {
            const previousMode = this.ui.currentMode;
            this.ui.currentMode = mode;
            this.notify("MODE_CHANGED", { 
                current: mode, 
                previous: previousMode 
            });
        }
    }
    
    /**
     * Create or update a prompt addition
     * @param {PromptAddition} addition - Addition data
     * @returns {Promise<boolean>} Success status
     */
    async saveAddition(addition) {
        try {
            this.setLoading(true);
            const serverData = await ApiOperations.writePromptAddition(addition);
            
            if (serverData) {
                this.updateFromServerData(serverData);
                this.notify("ADDITION_SAVED", { addition: addition.name });
                return true;
            }
            return false;
        } catch (error) {
            console.error("Failed to save addition:", error);
            this.notifyError("SAVE_ERROR", error);
            return false;
        } finally {
            this.setLoading(false);
        }
    }
    
    /**
     * Delete a prompt addition
     * @param {string} additionName - Name of addition to delete
     * @returns {Promise<boolean>} Success status
     */
    async deleteAddition(additionName) {
        try {
            this.setLoading(true);
            const serverData = await ApiOperations.deletePromptAddition(additionName);
            
            if (serverData) {
                // Clear selection if deleted item was selected
                if (this.ui.selectedAddition === additionName) {
                    this.ui.selectedAddition = null;
                }
                
                this.updateFromServerData(serverData);
                this.notify("ADDITION_DELETED", { addition: additionName });
                return true;
            }
            return false;
        } catch (error) {
            console.error("Failed to delete addition:", error);
            this.notifyError("DELETE_ERROR", error);
            return false;
        } finally {
            this.setLoading(false);
        }
    }
    
    /**
     * Create or update a prompt group
     * @param {PromptGroup} group - Group data
     * @returns {Promise<boolean>} Success status
     */
    async saveGroup(group) {
        try {
            this.setLoading(true);
            const serverData = await ApiOperations.writePromptGroup(group);
            
            if (serverData) {
                this.updateFromServerData(serverData);
                this.notify("GROUP_SAVED", { group: group.id || group.name });
                return true;
            }
            return false;
        } catch (error) {
            console.error("Failed to save group:", error);
            this.notifyError("SAVE_ERROR", error);
            return false;
        } finally {
            this.setLoading(false);
        }
    }
    
    /**
     * Delete a prompt group
     * @param {number} groupId - ID of group to delete
     * @returns {Promise<boolean>} Success status
     */
    async deleteGroup(groupId) {
        try {
            this.setLoading(true);
            const serverData = await ApiOperations.deletePromptGroup(groupId);
            
            if (serverData) {
                // Clear selection if deleted item was selected
                if (this.ui.selectedGroup === groupId) {
                    this.ui.selectedGroup = null;
                }
                
                this.updateFromServerData(serverData);
                this.notify("GROUP_DELETED", { group: groupId });
                return true;
            }
            return false;
        } catch (error) {
            console.error("Failed to delete group:", error);
            this.notifyError("DELETE_ERROR", error);
            return false;
        } finally {
            this.setLoading(false);
        }
    }
    
    /**
     * Get current state snapshot
     * @returns {Object} Current state
     */
    getState() {
        return {
            data: JSON.parse(JSON.stringify(this.data)),
            ui: { ...this.ui }
        };
    }
    
    /**
     * Get additions as array (for compatibility)
     * @returns {PromptAddition[]} Array of additions
     */
    getAdditionsArray() {
        return Object.values(this.data.additions);
    }
    
    /**
     * Get addition by name
     * @param {string} name - Addition name
     * @returns {PromptAddition|null} Addition data or null
     */
    getAddition(name) {
        return this.data.additions[name] || null;
    }
    
    /**
     * Get group by ID
     * @param {number} id - Group ID
     * @returns {PromptGroup|null} Group data or null
     */
    getGroup(id) {
        return this.data.groups.find(g => g.id === id) || null;
    }
    
    /**
     * Check if data needs refresh from server
     * @returns {boolean} True if refresh needed
     */
    needsRefresh() {
        const MAX_AGE = 5 * 60 * 1000; // 5 minutes
        return Date.now() - this.data.lastSync > MAX_AGE;
    }
}

// Create singleton instance
export const promptState = new PromptState();

// Auto-initialize when imported
promptState.initialize().catch(error => {
    console.error("Failed to auto-initialize prompt state:", error);
});