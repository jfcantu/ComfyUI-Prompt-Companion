import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

/**
 * API Operations for Prompt Companion extension
 * Handles all communication with the backend API endpoints
 */
export const ApiOperations = {
    /**
     * Get all prompt additions and groups from the server
     * @returns {Promise<Object|null>} Promise resolving to prompt data or null on error
     */
    async getPromptAdditions() {
        try {
            const resp = await api.fetchApi("/prompt-companion/prompt-addition", { method: "GET" });
            
            if (!resp.ok) {
                const errorData = await resp.json().catch(() => ({ message: "Unknown error" }));
                console.error("API Error:", errorData);
                alert(`Error loading prompt additions: ${errorData.message || "Unknown error"}`);
                return null;
            }

            const responseData = await resp.json();
            
            // Handle both old and new response formats
            if (responseData.success !== undefined) {
                // New standardized format
                if (!responseData.success) {
                    console.error("API Error:", responseData.errors);
                    alert(`Error loading prompt additions: ${responseData.message}`);
                    return null;
                }
                return responseData.data;
            } else {
                // Legacy format - direct data
                return responseData;
            }
        } catch (error) {
            console.error("Network error getting prompt additions:", error);
            alert(`Network error loading prompt additions: ${error.message}`);
            return null;
        }
    },

    /**
     * Create or update a prompt addition on the server
     * @param {Object} promptAddition - The prompt addition data to save
     * @returns {Promise<Object|null>} Promise resolving to updated prompt data or null on error
     */
    async writePromptAddition(promptAddition) {
        try {
            const resp = await api.fetchApi(`/prompt-companion/prompt-addition`, {
                method: "POST",
                body: JSON.stringify(promptAddition)
            });

            if (!resp.ok) {
                const errorData = await resp.json().catch(() => ({ message: "Unknown error" }));
                console.error("API Error:", errorData);
                alert(`Error saving prompt addition: ${errorData.message || "Unknown error"}`);
                return null;
            }

            const responseData = await resp.json();
            
            // Handle both old and new response formats
            if (responseData.success !== undefined) {
                // New standardized format - return full response for quickSave to check
                return responseData;
            } else {
                // Legacy format - wrap in success response
                return {
                    success: true,
                    data: responseData,
                    message: "Prompt addition saved successfully"
                };
            }
        } catch (error) {
            console.error("Network error saving prompt addition:", error);
            alert(`Network error saving prompt addition: ${error.message}`);
            return null;
        }
    },

    /**
     * Delete a prompt addition from the server
     * @param {string} promptAdditionName - Name of the prompt addition to delete
     * @returns {Promise<Object|null>} Promise resolving to updated prompt data or null on error
     */
    async deletePromptAddition(promptAdditionName) {
        try {
            // URL encode the name to handle special characters
            const encodedName = encodeURIComponent(promptAdditionName);
            const resp = await api.fetchApi(`/prompt-companion/prompt-addition/${encodedName}`, {
                method: "DELETE",
            });

            if (!resp.ok) {
                const errorData = await resp.json().catch(() => ({ message: "Unknown error" }));
                console.error("API Error:", errorData);
                alert(`Error deleting prompt addition: ${errorData.message || "Unknown error"}`);
                return null;
            }

            const responseData = await resp.json();
            
            // Handle both old and new response formats
            if (responseData.success !== undefined) {
                // New standardized format
                if (!responseData.success) {
                    console.error("API Error:", responseData.errors);
                    alert(`Error deleting prompt addition: ${responseData.message}`);
                    return null;
                }
                return responseData.data;
            } else {
                // Legacy format - direct data
                return responseData;
            }
        } catch (error) {
            console.error("Network error deleting prompt addition:", error);
            alert(`Network error deleting prompt addition: ${error.message}`);
            return null;
        }
    },

    async savePromptAdditionAs(node) {
        // implement later
        //    const promptAdditionTriggerWords = node.promptAdditionTriggerWordsWidget.value;
        const promptAdditionTriggerWords = "";
        const promptAdditionText = node.positiveAdditionWidget?.value || "";

        app.extensionManager.dialog.prompt({
            title: "Save As",
            message: `Save this prompt addition as:`
        }).then(async result => {
            if (result) {
                const promptAddition = {
                    name: result.trim(),
                    trigger_words: promptAdditionTriggerWords,
                    positive_prompt_addition_text: promptAdditionText,
                    negative_prompt_addition_text: node.negativeAdditionWidget?.value || ""
                };
                try {
                    await ApiOperations.writePromptAddition(promptAddition);
                    // Update the selected addition name and refresh data
                    if (node.promptAdditionNameWidget) {
                        node.promptAdditionNameWidget.value = result.trim();
                        if (node.promptAdditionNameWidget.callback) {
                            node.promptAdditionNameWidget.callback();
                        }
                    }
                } catch (e) {

                }
            }
        });
    },

    /**
     * Prompt Group API Operations
     */
    
    /**
     * Get all prompt groups from the server
     * @returns {Promise<Object|null>} Promise resolving to prompt groups data or null on error
     */
    async getPromptGroups() {
        try {
            const resp = await api.fetchApi("/prompt-companion/prompt-group", { method: "GET" });
            
            if (!resp.ok) {
                const errorData = await resp.json().catch(() => ({ message: "Unknown error" }));
                console.error("API Error:", errorData);
                alert(`Error loading prompt groups: ${errorData.message || "Unknown error"}`);
                return null;
            }

            const responseData = await resp.json();
            
            // Handle both old and new response formats
            if (responseData.success !== undefined) {
                // New standardized format
                if (!responseData.success) {
                    console.error("API Error:", responseData.errors);
                    alert(`Error loading prompt groups: ${responseData.message}`);
                    return null;
                }
                return responseData.data;
            } else {
                // Legacy format - direct data
                return responseData;
            }
        } catch (error) {
            console.error("Network error getting prompt groups:", error);
            alert(`Network error loading prompt groups: ${error.message}`);
            return null;
        }
    },

    /**
     * Create or update a prompt group on the server
     * @param {Object} promptGroup - The prompt group data to save
     * @returns {Promise<Object|null>} Promise resolving to updated prompt data or null on error
     */
    async writePromptGroup(promptGroup) {
        try {
            const resp = await api.fetchApi(`/prompt-companion/prompt-group`, {
                method: "POST",
                body: JSON.stringify(promptGroup)
            });

            if (!resp.ok) {
                const errorData = await resp.json().catch(() => ({ message: "Unknown error" }));
                console.error("API Error:", errorData);
                alert(`Error saving prompt group: ${errorData.message || "Unknown error"}`);
                return null;
            }

            const responseData = await resp.json();
            
            // Handle both old and new response formats
            if (responseData.success !== undefined) {
                // New standardized format
                if (!responseData.success) {
                    console.error("API Error:", responseData.errors);
                    alert(`Error saving prompt group: ${responseData.message}`);
                    return null;
                }
                return responseData.data;
            } else {
                // Legacy format - direct data
                return responseData;
            }
        } catch (error) {
            console.error("Network error saving prompt group:", error);
            alert(`Network error saving prompt group: ${error.message}`);
            return null;
        }
    },

    /**
     * Delete a prompt group from the server
     * @param {number} promptGroupId - ID of the prompt group to delete
     * @returns {Promise<Object|null>} Promise resolving to updated prompt data or null on error
     */
    async deletePromptGroup(promptGroupId) {
        try {
            const resp = await api.fetchApi(`/prompt-companion/prompt-group/${promptGroupId}`, {
                method: "DELETE",
            });

            if (!resp.ok) {
                const errorData = await resp.json().catch(() => ({ message: "Unknown error" }));
                console.error("API Error:", errorData);
                alert(`Error deleting prompt group: ${errorData.message || "Unknown error"}`);
                return null;
            }

            const responseData = await resp.json();
            
            // Handle both old and new response formats
            if (responseData.success !== undefined) {
                // New standardized format
                if (!responseData.success) {
                    console.error("API Error:", responseData.errors);
                    alert(`Error deleting prompt group: ${responseData.message}`);
                    return null;
                }
                return responseData.data;
            } else {
                // Legacy format - direct data
                return responseData;
            }
        } catch (error) {
            console.error("Network error deleting prompt group:", error);
            alert(`Network error deleting prompt group: ${error.message}`);
            return null;
        }
    }
}