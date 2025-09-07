import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

async function getPromptAdditions() {
    const resp = await api.fetchApi("/prompt-companion/prompt-addition", { method: "GET" });

    if (resp.status !== 200) {

        alert(`Error loading prompt additions from server`);
        return;
    }

    return await resp.json();
}

async function writePromptAddition(promptAddition) {
    const resp = await api.fetchApi(`/prompt-companion/prompt-addition`, {
        method: "POST",
        body: JSON.stringify(promptAddition)
    });

    if (resp.status !== 200) {

        alert(`Error saving prompt addition to server`);
        return;
    };

    return await resp.json();
}

async function deletePromptAddition(promptAdditionName) {
    const resp = await api.fetchApi(`/prompt-companion/prompt-addition/${promptAdditionName}`, {
        method: "DELETE",
    });

    if (resp.status !== 200) {

        alert(`Error deleting prompt addition from server`);
        return;
    };

    return await resp.json();
}

async function savePromptAdditionAs(node) {
    // implement later
    //    const promptAdditionTriggerWords = node.promptAdditionTriggerWordsWidget.value;
    const promptAdditionTriggerWords = "";
    const promptAdditionText = node.promptAdditionTextWidget.value;

    app.extensionManager.dialog.prompt({
        title: "Save As",
        message: `Save this prompt addition as:`
    }).then(result => {
        if (result) {
            const promptAddition = {
                name: result.trim(),
                trigger_words: promptAdditionTriggerWords,
                prompt_addition_text: promptAdditionText
            };
            try {
                writePromptAddition(promptAddition);
            } catch (e) {

            }
        }
    });
}

app.registerExtension({
    name: "ComfyUI.Prompt.Companion",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeType.comfyClass == "PromptCompanion") {
            nodeType.prototype.refreshPromptAdditionWidgets = function (node) {
                node.promptAdditionNameComboWidget.options = { values: Object.keys(this.promptAdditions) };
                const originalAdditionName = node.promptAdditionNameComboWidget.value;

                if (!node.promptAdditionNameComboWidget.value) {
                    node.promptAdditionTextWidget.value = "";
                    return;
                }

                if (node.promptAdditionNameComboWidget.options.values.includes(originalAdditionName)) {
                    node.promptAdditionNameComboWidget.value = originalAdditionName;
                } else {
                    node.promptAdditionNameComboWidget.value = node.promptAdditionNameComboWidget.options.values[0];
                }
                node.promptAdditionTextWidget.value = this.promptAdditions[node.promptAdditionNameComboWidget.value].prompt_addition_text;
            };
            nodeType.prototype.updatePromptAdditions = function (node, promptAdditions) {
                const originalAdditionName = node.promptAdditionNameComboWidget.value;

                let newPromptAdditionsObject = {};
                for (const promptAddition of promptAdditions) {
                    newPromptAdditionsObject[promptAddition.name] = promptAddition;
                }

                this.promptAdditions = newPromptAdditionsObject;
                this.promptAdditionNames = Object.keys(this.promptAdditions);
                this.refreshPromptAdditionWidgets(node);
            }
        }
    },
    async nodeCreated(node) {
        if (node.comfyClass == "PromptCompanion") {

            node.promptAdditions = {};
            node.promptAdditionNames = {}

            node.promptAdditionNameComboWidget = node.widgets?.filter((w) => w.name === "prompt_addition_name")[0];
            // implement later
            // node.promptAdditionTriggerWordsWidget = node.widgets?.filter((w) => w.name === "prompt_addition_trigger_words")[0];
            node.promptAdditionTextWidget = node.widgets?.filter((w) => w.name === "prompt_addition_text")[0];

            node.addWidget("button", "Save", "save_prompt_addition", () => {
                const promptAdditionName = node.promptAdditionNameComboWidget.value;
                // const promptAdditionTriggerWords = node.promptAdditionTriggerWordsWidget.value;
                const promptAdditionTriggerWords = "";
                const promptAdditionText = node.promptAdditionTextWidget.value;

                if (!promptAdditionName) {
                    savePromptAdditionAs(node);
                } else {

                    app.extensionManager.dialog.confirm({
                        title: "Confirm Save",
                        message: `Are you sure you want to save ${promptAdditionName}?`,
                        type: "overwrite"
                    }).then(result => {
                        if (result) {
                            const promptAddition = {
                                name: promptAdditionName,
                                trigger_words: promptAdditionTriggerWords,
                                prompt_addition_text: promptAdditionText
                            };
                            try {
                                writePromptAddition(promptAddition);
                            } catch (e) {

                            }
                        }
                    });
                }
            });
            node.addWidget("button", "Save As...", "save_prompt_addition_as", () => {
                savePromptAdditionAs(node)
            });
            node.addWidget("button", "Delete", "delete_prompt_addition", () => {
                const promptAdditionName = node.promptAdditionNameComboWidget.value;

                app.extensionManager.dialog.confirm({
                    title: "Confirm Delete",
                    message: `Are you sure you want to delete ${promptAdditionName}?`,
                    type: "delete"
                }).then(result => {
                    if (result) {
                        try {
                            deletePromptAddition(promptAdditionName);
                        } catch (e) {

                        }
                    }
                });
            }
            );

            const promptAdditions = await getPromptAdditions();
            node.updatePromptAdditions(node, promptAdditions);

            node.promptAdditionNameComboWidget.callback = () => {
                let newValue = "";
                if (node.promptAdditions) {
                    if (node.promptAdditionNameComboWidget.value in node.promptAdditions) {
                        newValue = node.promptAdditions[node.promptAdditionNameComboWidget.value].prompt_addition_text || "";
                    }
                }
                node.promptAdditionTextWidget.value = newValue;
            }

            api.addEventListener("prompt-companion.addition-list", event => {
                node.updatePromptAdditions(node, event.detail);
            });
        }
    }
});