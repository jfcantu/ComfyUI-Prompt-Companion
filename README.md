# ComfyUI Prompt Companion

A ComfyUI extension for managing and organizing prompt additions with support for individual prompts, prompt groups, and automatic trigger-word matching.

## 🚀 Features

### Core Functionality
- **Individual Prompt Management**: Create, edit, and organize individual prompt additions.
- **Prompt Groups**: Group related prompt additons together for batch operations.
- **Multiple Operation Modes**: Choose between applying an individual prompt addition, a specific group of prompt additions, or automatically apply groups of prompt additions based on the checkpoint name.

## 📦 Installation

### Quick Install (Recommended)

This will be available once I'm happy enough with this node to publish it to the repository.

1. ~~Install [ComfyUI](https://docs.comfy.org/get_started)~~
2. ~~Install [ComfyUI-Manager](https://github.com/ltdrdata/ComfyUI-Manager)~~
3. ~~Look up "ComfyUI Prompt Companion" in ComfyUI-Manager and install~~
4. ~~Restart ComfyUI~~

### Manual Install
1. Clone this repository to your ComfyUI custom nodes directory:
   ```bash
   cd ComfyUI/custom_nodes/
   git clone https://github.com/jfcantu/ComfyUI-Prompt-Companion.git
   ```
2. Restart ComfyUI
3. The Prompt Companion node will be available in the `jfc` category

## 🎯 Usage

### Basic Setup

1. **Add the Node**: Search for "PromptCompanion" in the node browser and add it to your workflow.

2. **Configure Inputs**:
   - `ckpt_name`: Select your checkpoint.
   - `addition_type`: Choose "Individual" mode to select an individual prompt addition, or "Group" mode to apply one or more groups of prompt additions.
   - `prompt_group_mode`: Only available in "Group" mode. Choose "Manual" to select a single prompt addition, or "Automatic" to apply multiple groups based on the checkpoint name.
   - `combine_mode`: Specify whether your prompt additions go in front of your prompts (prepend) or after them (append).
   - `prompt_addition_name`: Only available in "Individual" mode. Select the prompt addition to apply.
   - `prompt_addition_group`: Only available in "Group" addition mode when "Manual" group mode is selected. Select a prompt addition group to apply.
   - `positive_addition`/`negative_addition`:
     - In Individual mode, you can edit your prompt addition here directly.
     - In Group mode, this will display the collected prompt additions that will be applied, which cannot be edited.
   - `positive_prompt`/`negative_prompt`: Your base prompts. Can be input from another node, or entered directly.
   
   

### Managing Prompt Additions

Start by right-clicking the node, and selecting "Edit Prompt Additions."

#### Adding/Modifying Prompt Additions

Pretty self-explanatory. Create, delete, modify, rename, save with a new name.

#### Adding/Modifying Prompt Groups

Click "Create New" to create a new one, or select one from the list to edit an exiting one.

"Trigger words" are strings that Prompt Companion will look for in your checkpoint name/path. If they match any part of it, the prompt group will be included in the list of additions.

While a prompt group is selected, select individual prompt additions to add/remove them from the prompt group.

Select "(none)" or click "Cancel" to exit.

**NOTE**: You can't edit prompt additions while editing a Prompt Group.

## 🔧 Architecture

### Frontend Components
- **`extension.js`**: Main ComfyUI extension registration and node behavior
- **`promptAdditionManager.js`**: Dialog manager for CRUD operations
- **`api-operations.js`**: HTTP client for backend communication
- **`state-manager.js`**: Centralized state management with event system

### Backend Components
- **`nodes.py`**: ComfyUI node definition and API endpoints
- **`extension_config.py`**: Data models and configuration management
- **`config-schema.json`**: JSON schema for data validation

### Debug Mode

Enable debug logging by opening browser developer tools:

```javascript
// Check current state
console.log(window.promptState?.getState());
```

## 🧪 Development

### Setup

To install the dev dependencies and pre-commit:

```bash
cd ComfyUI-Prompt-Companion
pip install -e .[dev]
pre-commit install
```

### Project Structure

```
ComfyUI-Prompt-Companion/
├── src/
│   ├── web/                     # Frontend JavaScript modules
│   │   ├── extension.js         # Main ComfyUI extension
│   │   ├── promptAdditionManager.js  # UI dialog manager
│   │   ├── api-operations.js    # HTTP client
│   │   └── state-manager.js     # State management
│   ├── nodes.py                 # Backend node and API
│   ├── extension_config.py      # Data models and config
│   └── config-schema.json       # Data validation schema
├── __init__.py                  # Python module initialization
└── README.md                    # This file
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with proper documentation
4. Add tests for new functionality
5. Submit a pull request