import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

export const ApiOperations = {
    async getPromptAdditions() {
        const resp = await api.fetchApi("/prompt-companion/prompt-addition", { method: "GET" });

        if (resp.status !== 200) {
            alert(`Error loading prompt additions from server`);
            return;
        }

        return await resp.json();
    },

    async writePromptAddition(promptAddition) {
        const resp = await api.fetchApi(`/prompt-companion/prompt-addition`, {
            method: "POST",
            body: JSON.stringify(promptAddition)
        });

        if (resp.status !== 200) {
            alert(`Error saving prompt addition to server`);
            return;
        };

        return await resp.json();
    },

    async deletePromptAddition(promptAdditionName) {
        const resp = await api.fetchApi(`/prompt-companion/prompt-addition/${promptAdditionName}`, {
            method: "DELETE",
        });

        if (resp.status !== 200) {
            alert(`Error deleting prompt addition from server`);
            return;
        };

        return await resp.json();
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

    // Prompt Group operations
    async getPromptGroups() {
        const resp = await api.fetchApi("/prompt-companion/prompt-group", { method: "GET" });

        if (resp.status !== 200) {
            alert(`Error loading prompt groups from server`);
            return;
        }

        return await resp.json();
    },

    async writePromptGroup(promptGroup) {
        const resp = await api.fetchApi(`/prompt-companion/prompt-group`, {
            method: "POST",
            body: JSON.stringify(promptGroup)
        });

        if (resp.status !== 200) {
            alert(`Error saving prompt group to server`);
            return;
        };

        return await resp.json();
    },

    async deletePromptGroup(promptGroupId) {
        const resp = await api.fetchApi(`/prompt-companion/prompt-group/${promptGroupId}`, {
            method: "DELETE",
        });

        if (resp.status !== 200) {
            alert(`Error deleting prompt group from server`);
            return;
        };

        return await resp.json();
    }
}