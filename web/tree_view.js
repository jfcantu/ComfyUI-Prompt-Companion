/*
 * Tree View Component for ComfyUI-Prompt-Companion
 * 
 * This file implements the hierarchical tree view for managing folders and subprompts
 * within the ComfyUI-Prompt-Companion interface.
 */

import { api } from "../../../scripts/api.js";
import { $el } from "../../../scripts/ui.js";

class PromptTreeView {
    constructor(container) {
        this.container = typeof container === 'string' ? document.getElementById(container) : container;
        this.treeData = {};
        this.selectedItems = new Set();
        this.expandedFolders = new Set();
        this.searchTerm = '';
        this.sortMode = 'name';
        this.onSelectionChange = null;
        this.draggedItem = null;
        this.contextMenu = null;
        
        if (!this.container) {
            console.error("Tree view container not found");
            return;
        }
        
        this.initialize();
    }
    
    initialize() {
        this.injectStyles();
        this.createTreeStructure();
        this.setupEventHandlers();
        this.loadTreeData();
    }
    
    /**
     * Inject necessary CSS styles for the tree view
     */
    injectStyles() {
        const styleId = 'prompt-companion-tree-styles';
        if (document.getElementById(styleId)) return; // Already injected
        
        const style = document.createElement('style');
        style.id = styleId;
        style.textContent = `
            .prompt-companion-tree-item.drag-over {
                background-color: rgba(0, 122, 204, 0.2) !important;
                border: 2px dashed rgba(0, 122, 204, 0.5) !important;
                border-radius: 4px !important;
            }
            
            .prompt-companion-tree-item.drag-over .prompt-companion-tree-item-content {
                background-color: transparent !important;
            }
        `;
        
        document.head.appendChild(style);
    }
    
    createTreeStructure() {
        this.container.innerHTML = '';
        this.container.className = 'prompt-companion-tree';
        
        // Create tree content area
        this.treeContent = $el("div", {
            className: "prompt-companion-tree-content"
        });
        
        this.container.appendChild(this.treeContent);
    }
    
    setupEventHandlers() {
        // Global click handler to close context menu
        document.addEventListener('click', (e) => {
            if (this.contextMenu && !this.contextMenu.contains(e.target)) {
                this.hideContextMenu();
            }
        });
        
        // Handle clicks on empty areas to deselect items
        this.treeContent.addEventListener('click', async (e) => {
            // Only handle clicks on the tree content itself (empty areas)
            if (e.target === this.treeContent) {
                // Check if we currently have a selection
                if (this.selectedItems.size > 0 && this.onSelectionChange) {
                    // Clear selection and trigger callback with null (deselection)
                    this.selectedItems.clear();
                    this.updateSelection();
                    await this.onSelectionChange(null);
                }
            }
        });
        
        // Keyboard shortcuts
        this.container.addEventListener('keydown', (e) => {
            this.handleKeyboard(e);
        });
        
        this.container.setAttribute('tabindex', '0');
    }
    
    async loadTreeData(skipRender = false) {
        try {
            // Fetch both subprompts and folders simultaneously
            const [subpromptsResponse, foldersResponse] = await Promise.all([
                api.fetchApi("/prompt_companion/subprompts"),
                api.fetchApi("/prompt_companion/folders")
            ]);
            
            if (subpromptsResponse.ok && foldersResponse.ok) {
                const subpromptsData = await subpromptsResponse.json();
                const foldersData = await foldersResponse.json();
                
                // Organize tree data with both subprompts and folders
                this.treeData = this.organizeTreeData(subpromptsData, foldersData);
                if (!skipRender) {
                    this.renderTree();
                }
            } else {
                // Handle partial failures - try to work with what we have
                let subpromptsData = [];
                let foldersData = [];
                
                if (subpromptsResponse.ok) {
                    subpromptsData = await subpromptsResponse.json();
                } else {
                    console.error("Subprompts response failed:", subpromptsResponse.status, subpromptsResponse.statusText);
                }
                
                if (foldersResponse.ok) {
                    foldersData = await foldersResponse.json();
                } else {
                    console.error("Folders response failed:", foldersResponse.status, foldersResponse.statusText);
                }
                
                // Ensure data is in expected format (arrays)
                if (!Array.isArray(subpromptsData)) {
                    console.warn("Subprompts data is not an array, converting:", subpromptsData);
                    subpromptsData = [];
                }
                if (!Array.isArray(foldersData)) {
                    console.warn("Folders data is not an array, converting:", foldersData);
                    foldersData = [];
                }
                
                // Organize with whatever data we have
                this.treeData = this.organizeTreeData(subpromptsData, foldersData);
                if (!skipRender) {
                    this.renderTree();
                }
                
                if (!subpromptsResponse.ok || !foldersResponse.ok) {
                    this.showError("Some data failed to load, showing partial results");
                }
            }
        } catch (error) {
            console.error("Error loading tree data:", error);
            this.showError(`Error loading tree data: ${error.message}`);
        }
    }
    
    organizeTreeData(subprompts = [], foldersData = []) {
        // Ensure subprompts is an array
        if (!Array.isArray(subprompts)) {
            console.warn("organizeTreeData: subprompts is not an array:", subprompts);
            subprompts = [];
        }
        
        // Ensure foldersData is an array
        if (!Array.isArray(foldersData)) {
            console.warn("organizeTreeData: foldersData is not an array:", foldersData);
            foldersData = [];
        }
        const organized = {
            folders: {},
            items: {}
        };
        
        // Build folder lookup and hierarchy from Folder objects
        const folderLookup = {};
        
        // First pass: process all folder objects and build lookup
        foldersData.forEach(folderObj => {
            const folderId = folderObj.id;
            const folderData = {
                id: folderId,
                name: folderObj.name,
                parent_id: folderObj.parent_id,
                children: [],
                subfolders: [],
                expanded: this.expandedFolders.has(folderId),
                type: 'folder'
            };
            
            organized.folders[folderId] = folderData;
            folderLookup[folderId] = folderObj;
        });
        
        // Create virtual root folder if it doesn't exist
        const rootFolderId = 'root';
        if (!organized.folders[rootFolderId]) {
            organized.folders[rootFolderId] = {
                id: rootFolderId,
                name: 'Root',
                parent_id: null,
                children: [],
                subfolders: [],
                expanded: this.expandedFolders.has(rootFolderId),
                type: 'folder'
            };
        }
        
        // Second pass: collect all subprompts and assign them to folders
        subprompts.forEach(subprompt => {
            const subpromptId = subprompt.id;
            
            // Determine which folder this subprompt belongs to
            let targetFolderId = rootFolderId; // Default to root
            
            // Handle both legacy folder_path and new folder_id references
            if (subprompt.folder_id && organized.folders[subprompt.folder_id]) {
                targetFolderId = subprompt.folder_id;
            } else if (subprompt.folder_path) {
                // Legacy support: find folder by path
                targetFolderId = this.findFolderIdByPath(subprompt.folder_path, folderLookup) || rootFolderId;
            }
            
            // Create subprompt item
            organized.items[subpromptId] = {
                ...subprompt,
                id: subpromptId,
                name: subprompt.name,
                type: 'subprompt',
                folderId: targetFolderId,
                folderPath: subprompt.folder_path || '' // Keep for backward compatibility
            };
            
            // Add to target folder's children
            if (organized.folders[targetFolderId]) {
                organized.folders[targetFolderId].children.push(subpromptId);
            }
        });
        
        // Third pass: build folder hierarchy
        const rootFolders = [];
        Object.values(organized.folders).forEach(folder => {
            if (!folder.parent_id || folder.id === rootFolderId) {
                // This is a root-level folder
                if (folder.id !== rootFolderId) {
                    rootFolders.push(folder);
                }
            } else {
                // This has a parent - add to parent's subfolders
                const parentFolder = organized.folders[folder.parent_id];
                if (parentFolder) {
                    parentFolder.subfolders.push(folder);
                } else {
                    // Parent not found, treat as root folder
                    rootFolders.push(folder);
                }
            }
        });
        
        organized.rootFolders = rootFolders;
        organized.rootFolder = organized.folders[rootFolderId];
        return organized;
    }
    
    /**
     * Helper method to find folder ID by legacy path
     */
    findFolderIdByPath(path, folderLookup) {
        if (!path || path === '') {
            return 'root';
        }
        
        // Build reverse lookup from folder objects to find by path
        for (const [folderId, folderObj] of Object.entries(folderLookup)) {
            const folderPath = this.buildPathFromFolder(folderObj, folderLookup);
            if (folderPath === path) {
                return folderId;
            }
        }
        return null;
    }
    
    /**
     * Helper method to build path from folder object hierarchy
     */
    buildPathFromFolder(folder, folderLookup) {
        if (!folder || !folder.parent_id) {
            return folder ? folder.name : '';
        }
        
        const pathParts = [];
        let current = folder;
        const visited = new Set();
        
        while (current && !visited.has(current.id)) {
            visited.add(current.id);
            pathParts.unshift(current.name);
            
            if (current.parent_id) {
                current = folderLookup[current.parent_id];
            } else {
                break;
            }
        }
        
        return pathParts.join('/');
    }
    
    /**
     * Sort tree items with folders first, then subprompts, both alphabetically
     */
    sortTreeItems(folders = [], items = []) {
        // Sort folders alphabetically by name
        const sortedFolders = [...folders].sort((a, b) => {
            const nameA = (a.name || '').toLowerCase();
            const nameB = (b.name || '').toLowerCase();
            return nameA.localeCompare(nameB);
        });
        
        // Sort items (subprompts) alphabetically by name
        const sortedItems = [...items].sort((a, b) => {
            const nameA = (this.treeData.items[a]?.name || '').toLowerCase();
            const nameB = (this.treeData.items[b]?.name || '').toLowerCase();
            return nameA.localeCompare(nameB);
        });
        
        return { folders: sortedFolders, items: sortedItems };
    }
    
    renderTree() {
        if (!this.treeContent) return;
        
        this.treeContent.innerHTML = '';
        
        // Check if we have any content at all (subprompts OR folders)
        const hasSubprompts = Object.keys(this.treeData.items || {}).length > 0;
        const hasFolders = Object.keys(this.treeData.folders || {}).length > 1; // More than just root
        
        if (!hasSubprompts && !hasFolders) {
            this.treeContent.appendChild($el("div", {
                className: "prompt-companion-tree-empty",
                textContent: "No subprompts or folders found"
            }));
            return;
        }
        
        // Get the root folder
        const rootFolder = this.treeData.rootFolder || { id: 'root', name: 'Root', children: [], subfolders: [], expanded: true };
        
        // Sort and render root folder's subfolders and children
        const rootSorted = this.sortTreeItems(rootFolder.subfolders || [], rootFolder.children || []);
        
        // Render root folder's subfolders directly at level 0 (don't show the root folder itself)
        rootSorted.folders.forEach(subfolder => {
            this.renderFolder(subfolder, 0);
        });
        
        // Render root folder's children (subprompts) directly at level 0
        rootSorted.items.forEach(itemId => {
            const item = this.treeData.items[itemId];
            if (item && this.matchesSearch(item)) {
                const itemElement = this.createItemElement(item, 0);
                this.treeContent.appendChild(itemElement);
            }
        });
        
        // Sort and render other root folders (including empty ones)
        if (this.treeData.rootFolders) {
            const sortedRootFolders = [...this.treeData.rootFolders].sort((a, b) => {
                const nameA = (a.name || '').toLowerCase();
                const nameB = (b.name || '').toLowerCase();
                return nameA.localeCompare(nameB);
            });
            
            sortedRootFolders.forEach(folder => {
                this.renderFolder(folder, 0);
            });
        }
    }
    
    renderFolder(folder, level = 0) {
        if (!folder) return;
        
        const folderElement = this.createFolderElement(folder, level);
        this.treeContent.appendChild(folderElement);
        
        if (folder.expanded) {
            // Sort subfolders and items before rendering
            const sorted = this.sortTreeItems(folder.subfolders || [], folder.children || []);
            
            // Render subfolders first (alphabetically sorted)
            sorted.folders.forEach(subfolder => {
                this.renderFolder(subfolder, level + 1);
            });
            
            // Then render items (alphabetically sorted)
            sorted.items.forEach(itemId => {
                const item = this.treeData.items[itemId];
                if (item && this.matchesSearch(item)) {
                    const itemElement = this.createItemElement(item, level + 1);
                    this.treeContent.appendChild(itemElement);
                }
            });
        }
    }
    
    createFolderElement(folder, level) {
        const isExpanded = folder.expanded;
        const hasChildren = (folder.children && folder.children.length > 0) ||
                          (folder.subfolders && folder.subfolders.length > 0);
        
        // Show empty folders with a different icon to indicate they're empty
        const folderIcon = hasChildren ? "📁" : "📂"; // Open folder icon for empty folders
        const folderClass = hasChildren ? "" : " empty-folder";
        
        const element = $el("div", {
            className: `prompt-companion-tree-item prompt-companion-tree-folder${folderClass} ${isExpanded ? 'expanded' : ''}`,
            style: { paddingLeft: `${level * 20 + 10}px` },
            draggable: level > 0 && folder.id !== 'root', // Root folder is not draggable
            dataset: {
                type: 'folder',
                id: folder.id,
                level: level.toString()
            }
        }, [
            $el("div", {
                className: "prompt-companion-tree-item-content"
            }, [
                $el("span", {
                    className: `prompt-companion-tree-expander ${hasChildren ? 'has-children' : 'no-children'}`,
                    textContent: hasChildren ? (isExpanded ? '▼' : '▶') : '·', // Show dot for empty folders
                    onclick: (e) => {
                        e.stopPropagation();
                        if (hasChildren) {
                            this.toggleFolder(folder.id);
                        }
                    }
                }),
                $el("span", {
                    className: "prompt-companion-tree-icon",
                    textContent: folderIcon
                }),
                $el("span", {
                    className: "prompt-companion-tree-label",
                    textContent: folder.name || 'Root'
                })
            ])
        ]);
        
        // Add event listeners
        this.setupItemEventListeners(element, { type: 'folder', ...folder });
        
        // Add click handler to entire folder element for expand/collapse
        element.addEventListener('click', (e) => {
            // Only handle click if it's not on the expander itself (to avoid double-triggering)
            if (!e.target.classList.contains('prompt-companion-tree-expander')) {
                if (hasChildren) {
                    this.toggleFolder(folder.id);
                }
                // Prevent event from bubbling up
                e.stopPropagation();
            }
        });
        
        return element;
    }
    
    createItemElement(item, level) {
        const isSelected = this.selectedItems.has(item.id);
        
        // Determine icon and title based on whether subprompt has trigger words
        const hasTriggerWords = item.trigger_words && item.trigger_words.length > 0;
        const subpromptIcon = hasTriggerWords ? "⚡" : "📄"; // Lightning for automatic, document for manual
        const subpromptTitle = hasTriggerWords ?
            "Automatic subprompt (has trigger words)" :
            "Manual subprompt (no trigger words)";
        
        const element = $el("div", {
            className: `prompt-companion-tree-item prompt-companion-tree-subprompt ${isSelected ? 'selected' : ''}`,
            style: { paddingLeft: `${level * 20 + 10}px` },
            draggable: true,
            dataset: {
                type: 'subprompt',
                id: item.id,
                level: level.toString()
            }
        }, [
            $el("div", {
                className: "prompt-companion-tree-item-content"
            }, [
                // Add spacing to align with folder expander
                $el("span", {
                    className: "prompt-companion-tree-expander-spacer",
                    textContent: ' ',
                    style: { width: '16px', display: 'inline-block' }
                }),
                $el("span", {
                    className: "prompt-companion-tree-icon",
                    textContent: subpromptIcon,
                    title: subpromptTitle
                }),
                $el("span", {
                    className: "prompt-companion-tree-label",
                    textContent: item.name // Show clean name from UUID-based system
                }),
                $el("div", {
                    className: "prompt-companion-tree-item-info"
                }, [
                    hasTriggerWords ?
                        $el("span", {
                            className: "prompt-companion-tree-tags",
                            textContent: item.trigger_words.join(', '),
                            title: "Trigger words: " + item.trigger_words.join(', ')
                        }) : null
                ].filter(Boolean))
            ])
        ]);
        
        // Add event listeners
        this.setupItemEventListeners(element, item);
        
        return element;
    }
    
    setupItemEventListeners(element, item) {
        // Click selection
        element.addEventListener('click', (e) => {
            this.handleItemClick(e, item);
        });
        
        // Double-click to edit
        element.addEventListener('dblclick', (e) => {
            this.handleItemDoubleClick(e, item);
        });
        
        // Context menu
        element.addEventListener('contextmenu', (e) => {
            e.preventDefault();
            this.handleContextMenu(e, item);
        });
        
        // Drag and drop
        if (element.draggable) {
            element.addEventListener('dragstart', (e) => {
                this.handleDragStart(e, item);
            });
        }
        
        element.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'move';
            
            // Add highlighting during dragover to ensure it works across entire item area
            if (item.type === 'folder' && this.draggedItem) {
                e.currentTarget.classList.add('drag-over');
            }
        });
        
        element.addEventListener('dragenter', (e) => {
            e.preventDefault();
            this.handleDragEnter(e, item);
        });
        
        element.addEventListener('dragleave', (e) => {
            e.preventDefault();
            // Only remove highlighting if we're actually leaving the element
            // Check if the related target is not a child of the current element
            if (!e.currentTarget.contains(e.relatedTarget)) {
                this.handleDragLeave(e, item);
            }
        });
        
        element.addEventListener('drop', (e) => {
            e.preventDefault();
            this.handleDrop(e, item);
        });
    }
    
    async handleItemClick(event, item) {
        // Check for unsaved changes before changing selection
        if (this.onSelectionChange && this.onSelectionChange.checkUnsavedChanges) {
            const hasUnsavedChanges = await this.onSelectionChange.checkUnsavedChanges();
            if (hasUnsavedChanges) {
                // Let the edit dialog handle the unsaved changes dialog
                const canProceed = await this.onSelectionChange.handleUnsavedChanges();
                if (!canProceed) {
                    return; // Don't change selection
                }
            }
        }
        
        if (event.ctrlKey) {
            // Multi-select
            if (item.type === 'subprompt') {
                if (this.selectedItems.has(item.id)) {
                    this.selectedItems.delete(item.id);
                } else {
                    this.selectedItems.add(item.id);
                }
            }
        } else {
            // Single select
            this.selectedItems.clear();
            if (item.type === 'subprompt') {
                this.selectedItems.add(item.id);
            }
        }
        
        this.updateSelection();
        
        if (item.type === 'subprompt' && this.onSelectionChange) {
            this.onSelectionChange(item);
        } else if (item.type === 'folder' && this.onSelectionChange) {
            // When clicking on folder, deselect any subprompts (show placeholder panel)
            this.onSelectionChange(null);
        }
    }
    
    handleItemDoubleClick(event, item) {
        if (item.type === 'folder') {
            this.toggleFolder(item.id);
        } else if (item.type === 'subprompt') {
            // Open for editing
            if (window.PromptCompanion?.showEditDialog) {
                window.PromptCompanion.showEditDialog(item);
            }
        }
    }
    
    handleContextMenu(event, item) {
        this.showContextMenu(event, item);
    }
    
    showContextMenu(event, item) {
        this.hideContextMenu();
        
        const menuItems = this.getContextMenuItems(item);
        
        this.contextMenu = $el("div", {
            className: "prompt-companion-context-menu",
            style: {
                position: "fixed",
                left: `${event.clientX}px`,
                top: `${event.clientY}px`,
                zIndex: "10001"
            }
        }, menuItems.map(menuItem => {
            if (menuItem === null) {
                return $el("hr", { className: "prompt-companion-context-separator" });
            }
            
            return $el("div", {
                className: "prompt-companion-context-menu-item",
                textContent: menuItem.label,
                onclick: () => {
                    this.hideContextMenu();
                    menuItem.action(item);
                }
            });
        }));
        
        document.body.appendChild(this.contextMenu);
        
        // Adjust position if menu goes off-screen
        const rect = this.contextMenu.getBoundingClientRect();
        if (rect.right > window.innerWidth) {
            this.contextMenu.style.left = `${event.clientX - rect.width}px`;
        }
        if (rect.bottom > window.innerHeight) {
            this.contextMenu.style.top = `${event.clientY - rect.height}px`;
        }
    }
    
    getContextMenuItems(item) {
        const items = [];
        
        if (item.type === 'folder') {
            items.push(
                { label: "New Subprompt", action: () => this.createSubprompt(item.id) },
                { label: "New Folder", action: () => this.createFolderWithPrompt(item.id) },
                null
            );
            
            if (item.id && item.id !== 'root') {
                items.push(
                    { label: "Rename Folder", action: () => this.renameFolder(item) },
                    { label: "Delete Folder", action: () => this.deleteFolder(item) }
                );
            }
        } else if (item.type === 'subprompt') {
            items.push(
                { label: "Rename", action: () => this.renameSubprompt(item) },
                { label: "Duplicate", action: () => this.duplicateSubprompt(item) },
                null,
                { label: "Delete", action: () => this.deleteSubprompt(item) }
            );
        }
        
        return items;
    }
    
    hideContextMenu() {
        if (this.contextMenu) {
            if (this.contextMenu.parentNode) {
                this.contextMenu.parentNode.removeChild(this.contextMenu);
            }
            this.contextMenu = null;
        }
    }
    
    handleDragStart(event, item) {
        this.draggedItem = item;
        event.dataTransfer.effectAllowed = 'move';
        event.dataTransfer.setData('text/plain', JSON.stringify(item));
        
        // Add visual feedback
        event.target.style.opacity = '0.5';
    }
    
    handleDragEnter(event, item) {
        // Only highlight folders as valid drop targets
        if (item.type === 'folder') {
            event.currentTarget.classList.add('drag-over');
        }
    }
    
    handleDragLeave(event, item) {
        // Remove highlight when leaving the element
        if (item.type === 'folder') {
            event.currentTarget.classList.remove('drag-over');
        }
    }
    
    handleDrop(event, targetItem) {
        if (!this.draggedItem) return;
        
        // Reset visual feedback
        document.querySelectorAll('.prompt-companion-tree-item').forEach(el => {
            el.style.opacity = '';
            el.classList.remove('drag-over');
        });
        
        const sourceItem = this.draggedItem;
        this.draggedItem = null;
        
        // Don't allow dropping on itself or its current location
        if (sourceItem.type === 'subprompt' && targetItem.type === 'subprompt' && sourceItem.id === targetItem.id) {
            return;
        }
        if (sourceItem.type === 'folder' && targetItem.type === 'folder' && sourceItem.id === targetItem.id) {
            return;
        }
        
        // For subprompts: don't allow dropping into the same folder it's already in
        if (sourceItem.type === 'subprompt' && targetItem.type === 'folder') {
            const currentFolderId = sourceItem.folder_id || sourceItem.folderId || 'root';
            if (currentFolderId === targetItem.id) {
                return; // Already in this folder
            }
        }
        
        // Determine target folder ID
        let targetFolderId = 'root';
        if (targetItem.type === 'folder') {
            targetFolderId = targetItem.id;
        } else if (targetItem.type === 'subprompt') {
            targetFolderId = targetItem.folderId || 'root';
        }
        
        // Move the item
        this.moveItem(sourceItem, targetFolderId);
    }
    
    async moveItem(item, targetFolderId) {
        if (item.type === 'subprompt') {
            try {
                // Use UUID for API call
                const response = await api.fetchApi(`/prompt_companion/subprompts/${encodeURIComponent(item.id)}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        id: item.id, // Preserve UUID
                        name: item.name,
                        positive: item.positive || '',
                        negative: item.negative || '',
                        trigger_words: item.trigger_words || [],
                        order: item.order || ["attached"],
                        folder_id: targetFolderId === 'root' ? null : targetFolderId,
                        folder_path: "" // Keep empty for backward compatibility during transition
                    })
                });
                
                if (response.ok) {
                    await this.refreshTreePreservingState();
                } else {
                    console.error("Failed to move item");
                }
            } catch (error) {
                console.error("Error moving item:", error);
            }
        }
    }
    
    toggleFolder(folderId) {
        if (this.expandedFolders.has(folderId)) {
            this.expandedFolders.delete(folderId);
        } else {
            this.expandedFolders.add(folderId);
        }
        
        // Update folder state
        if (this.treeData.folders[folderId]) {
            this.treeData.folders[folderId].expanded = this.expandedFolders.has(folderId);
        }
        
        this.renderTree();
    }
    
    /**
     * Expand a folder by ID
     */
    expandFolder(folderId) {
        if (folderId !== null && folderId !== undefined) {
            this.expandedFolders.add(folderId);
            
            // Update folder state
            if (this.treeData.folders[folderId]) {
                this.treeData.folders[folderId].expanded = true;
            }
            
            this.renderTree();
        }
    }
    
    /**
     * Expand all parent folders of a given folder ID
     */
    expandParentFolders(folderId) {
        if (!folderId || folderId === 'root') return;
        
        const folder = this.treeData.folders[folderId];
        if (!folder) return;
        
        // Expand this folder
        this.expandedFolders.add(folderId);
        if (this.treeData.folders[folderId]) {
            this.treeData.folders[folderId].expanded = true;
        }
        
        // Recursively expand parent folders
        if (folder.parent_id && folder.parent_id !== 'root') {
            this.expandParentFolders(folder.parent_id);
        }
        
        // Only render if this is the top-level call (no tree refresh pending)
        // This prevents conflicting refreshes when called after refreshTreePreservingState()
        if (this._skipRenderOnExpand !== true) {
            this.renderTree();
        }
    }
    
    updateSelection() {
        // Update visual selection
        this.container.querySelectorAll('.prompt-companion-tree-item').forEach(element => {
            const id = element.dataset.id;
            if (id && this.selectedItems.has(id)) {
                element.classList.add('selected');
            } else {
                element.classList.remove('selected');
            }
        });
    }
    
    searchTree(term) {
        this.searchTerm = term.toLowerCase();
        this.renderTree();
    }
    
    matchesSearch(item) {
        if (!this.searchTerm) return true;
        
        const searchableText = [
            item.id,
            item.positive,
            item.negative,
            ...(item.trigger_words || [])
        ].join(' ').toLowerCase();
        
        return searchableText.includes(this.searchTerm);
    }
    
    sortTree(mode) {
        this.sortMode = mode;
        // Re-organize and render tree with new sort order
        this.renderTree();
    }
    
    async createFolder(folderName, parentId = 'root') {
        // If folderName is not provided, prompt for it (backwards compatibility)
        if (!folderName) {
            folderName = await this.showInputDialog("Enter folder name:", "");
            if (!folderName || !folderName.trim()) {
                return false;
            }
        }
        
        const name = folderName.trim();
        
        // Check if folder already exists in parent
        if (this.treeData.folders) {
            const existingFolder = Object.values(this.treeData.folders).find(
                folder => folder.name === name && folder.parent_id === (parentId === 'root' ? null : parentId)
            );
            if (existingFolder) {
                console.warn(`Folder "${name}" already exists in this location`);
                return false;
            }
        }
        
        // Use the new UUID-based folder creation API endpoint
        try {
            const response = await api.fetchApi('/prompt_companion/folders', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: name,
                    parent_id: parentId === 'root' ? null : parentId
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                // Expand the new folder and its parent
                this.expandedFolders.add(result.id);
                if (parentId !== 'root') {
                    this.expandedFolders.add(parentId);
                }
                await this.refreshTreePreservingState();
                return true;
            } else {
                console.error("Folder creation failed:", response.status, response.statusText);
                try {
                    const errorData = await response.json();
                    console.error(`Failed to create folder: ${errorData.error || 'Unknown error'}`);
                } catch (e) {
                    const errorText = await response.text();
                    console.error("Error response:", errorText);
                }
                return false;
            }
        } catch (error) {
            console.error("Error in createFolder:", error);
            return false;
        }
    }
    
    /**
     * Create folder with prompt (for context menu)
     */
    async createFolderWithPrompt(parentId = 'root') {
        const name = await this.showInputDialog("Enter folder name:", "");
        if (name && name.trim()) {
            return await this.createFolder(name.trim(), parentId);
        }
        return false;
    }
    
    async createSubprompt(parentId = 'root') {
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
                folder_id: parentId === 'root' ? null : parentId,
                folder_path: "", // Keep empty for backward compatibility during transition
                positive: '',
                negative: '',
                trigger_words: [],
                order: ["attached"]
            };
            
            const response = await api.fetchApi('/prompt_companion/subprompts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(newSubpromptData)
            });
            
            if (response.ok) {
                const savedSubprompt = await response.json();
                
                // Ensure parent folder is marked as expanded BEFORE refresh
                if (parentId !== 'root') {
                    this.expandedFolders.add(parentId);
                    // Also ensure all parent folders are expanded
                    const folder = this.treeData.folders && this.treeData.folders[parentId];
                    if (folder) {
                        let currentFolder = folder;
                        while (currentFolder && currentFolder.parent_id && currentFolder.parent_id !== 'root') {
                            this.expandedFolders.add(currentFolder.parent_id);
                            currentFolder = this.treeData.folders[currentFolder.parent_id];
                        }
                    }
                }
                
                // Refresh tree view to show new subprompt while preserving expanded state
                await this.refreshTreePreservingState();
                
                // Select the new subprompt
                this.selectedItems.clear();
                this.selectedItems.add(savedSubprompt.id);
                this.updateSelection();
                
                // Open edit dialog with the saved subprompt
                if (window.PromptCompanion?.showEditDialog) {
                    window.PromptCompanion.showEditDialog(savedSubprompt);
                }
            } else {
                const errorData = await response.json();
                await this.showAlertDialog(`Failed to create subprompt: ${errorData.error || 'Unknown error'}`);
            }
        } catch (error) {
            console.error("Error creating subprompt:", error);
            await this.showAlertDialog(`Error creating subprompt: ${error.message}`);
        }
    }
    
    editSubprompt(item) {
        if (window.PromptCompanion?.showEditDialog) {
            window.PromptCompanion.showEditDialog(item);
        }
    }
    
    async duplicateSubprompt(item) {
        const newName = `${item.name}_copy_${Date.now()}`;
        
        try {
            const response = await api.fetchApi('/prompt_companion/subprompts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: newName,
                    folder_id: item.folder_id || (item.folderId && item.folderId !== 'root' ? item.folderId : null),
                    folder_path: "", // Keep empty for backward compatibility during transition
                    positive: item.positive || '',
                    negative: item.negative || '',
                    trigger_words: item.trigger_words || [],
                    order: item.order || ["attached"]
                })
            });
            
            if (response.ok) {
                await this.refreshTreePreservingState();
            }
        } catch (error) {
            console.error("Error duplicating subprompt:", error);
        }
    }
    
    async renameSubprompt(item) {
        const newName = await this.showInputDialog("Enter new subprompt name:", item.name);
        if (!newName || newName.trim() === item.name) return;
        
        const trimmedName = newName.trim();
        
        // Validate name is not empty
        if (!trimmedName) {
            await this.showAlertDialog("Subprompt name cannot be empty");
            return;
        }
        
        // Check for duplicates in the same folder
        const currentFolderId = item.folder_id || item.folderId || 'root';
        const duplicateExists = Object.values(this.treeData.items || {}).some(otherItem =>
            otherItem.id !== item.id &&
            otherItem.name === trimmedName &&
            (otherItem.folder_id || otherItem.folderId || 'root') === currentFolderId
        );
        
        if (duplicateExists) {
            const folderName = currentFolderId === 'root' ? 'root folder' :
                (this.treeData.folders[currentFolderId]?.name || 'current folder');
            await this.showAlertDialog(`A subprompt named "${trimmedName}" already exists in ${folderName}`);
            return;
        }
        
        try {
            // Update the subprompt with the new name
            const response = await api.fetchApi(`/prompt_companion/subprompts/${encodeURIComponent(item.id)}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    id: item.id,
                    name: trimmedName,
                    positive: item.positive || '',
                    negative: item.negative || '',
                    trigger_words: item.trigger_words || [],
                    order: item.order || ["attached"],
                    folder_id: item.folder_id || (item.folderId && item.folderId !== 'root' ? item.folderId : null),
                    folder_path: item.folder_path || "" // Keep for backward compatibility
                })
            });
            
            if (response.ok) {
                const updatedItem = await response.json();
                
                // Update the tree view while preserving expanded state
                await this.refreshTreePreservingState();
                
                // Update the edit dialog if this subprompt is currently being edited
                if (window.PromptCompanion?.editDialog) {
                    const editDialog = window.PromptCompanion.editDialog;
                    if (editDialog && editDialog.currentSubprompt &&
                        editDialog.currentSubprompt.id === item.id) {
                        // Update the current subprompt reference and header
                        editDialog.currentSubprompt = updatedItem;
                        
                        // Calculate folder path for display
                        let displayFolderPath = "";
                        try {
                            if (updatedItem.folder_id) {
                                displayFolderPath = await editDialog.calculateFolderPath(updatedItem.folder_id);
                            } else if (updatedItem.folder_path) {
                                displayFolderPath = updatedItem.folder_path;
                            }
                        } catch (error) {
                            console.warn("Error calculating folder path for rename update:", error);
                            displayFolderPath = updatedItem.folder_path || "";
                        }
                        
                        editDialog.updateEditPanelHeader(updatedItem.name, displayFolderPath);
                    }
                }
                
                // Update node dropdowns in workflow
                if (window.PromptCompanion?.editDialog) {
                    window.PromptCompanion.editDialog.updateNodeDropdowns();
                }
                
                // Show success message
                if (window.PromptCompanion?.editDialog) {
                    window.PromptCompanion.editDialog.showMessage(`Subprompt renamed to "${trimmedName}" successfully`, "success");
                }
                
                return true;
            } else {
                const errorData = await response.json();
                await this.showAlertDialog(`Failed to rename subprompt: ${errorData.error || 'Unknown error'}`);
                return false;
            }
        } catch (error) {
            console.error("Error renaming subprompt:", error);
            await this.showAlertDialog(`Error renaming subprompt: ${error.message}`);
            return false;
        }
    }
    
    async deleteSubprompt(item) {
        const shouldDelete = await this.showConfirmDialog(`Are you sure you want to delete "${item.name}"?`);
        if (!shouldDelete) return;
        
        try {
            // Use UUID for API call
            const response = await api.fetchApi(`/prompt_companion/subprompts/${encodeURIComponent(item.id)}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                this.selectedItems.delete(item.id);
                
                // If this subprompt is currently being edited, clear the edit panel
                if (window.PromptCompanion?.editDialog) {
                    const editDialog = window.PromptCompanion.editDialog;
                    if (editDialog && editDialog.currentSubprompt &&
                        (editDialog.currentSubprompt.id === item.id || editDialog.currentSubprompt.name === item.name)) {
                        editDialog.clearForm();
                    }
                }
                
                await this.refreshTreePreservingState();
            }
        } catch (error) {
            console.error("Error deleting subprompt:", error);
        }
    }
    
    async deleteFolder(folder) {
        // Check if folder has contents (subfolders or subprompts)
        const hasContents = this.folderHasContents(folder);
        
        if (hasContents) {
            // Show smart deletion dialog
            const action = await this.showFolderDeletionDialog(folder);
            if (!action) return false; // User cancelled
            
            if (action === 'move') {
                return await this.deleteFolderAndMoveContents(folder);
            } else {
                return await this.deleteFolderAndAllContents(folder);
            }
        } else {
            // Empty folder, simple deletion
            const shouldDelete = await this.showConfirmDialog(`Are you sure you want to delete the empty folder "${folder.name}"?`);
            if (!shouldDelete) return false;
            return await this.deleteFolderAndAllContents(folder);
        }
    }
    
    /**
     * Check if folder has contents (subfolders or subprompts)
     */
    folderHasContents(folder) {
        const hasSubfolders = folder.subfolders && folder.subfolders.length > 0;
        const hasSubprompts = folder.children && folder.children.length > 0;
        return hasSubfolders || hasSubprompts;
    }
    
    /**
     * Show dialog asking user what to do with folder contents
     */
    async showFolderDeletionDialog(folder) {
        return new Promise((resolve) => {
            const dialog = $el("div", {
                className: "prompt-companion-deletion-dialog",
                style: {
                    position: "fixed",
                    top: "50%",
                    left: "50%",
                    transform: "translate(-50%, -50%)",
                    backgroundColor: "#2d2d2d",
                    border: "1px solid #404040",
                    borderRadius: "8px",
                    padding: "20px",
                    zIndex: "10002",
                    minWidth: "400px",
                    boxShadow: "0 4px 12px rgba(0,0,0,0.5)"
                }
            }, [
                $el("h3", {
                    textContent: `Delete Folder "${folder.name}"?`,
                    style: { color: "#ffffff", marginTop: "0", marginBottom: "15px" }
                }),
                $el("p", {
                    textContent: "This folder contains subprompts or subfolders. What would you like to do?",
                    style: { color: "#cccccc", marginBottom: "20px" }
                }),
                $el("div", {
                    className: "prompt-companion-dialog-buttons",
                    style: { display: "flex", gap: "10px", justifyContent: "flex-end" }
                }, [
                    $el("button", {
                        textContent: "Move Contents Up",
                        style: {
                            padding: "8px 16px",
                            backgroundColor: "#007acc",
                            color: "white",
                            border: "none",
                            borderRadius: "4px",
                            cursor: "pointer"
                        },
                        onclick: () => {
                            document.body.removeChild(overlay);
                            resolve('move');
                        }
                    }),
                    $el("button", {
                        textContent: "Delete All Contents",
                        style: {
                            padding: "8px 16px",
                            backgroundColor: "#dc3545",
                            color: "white",
                            border: "none",
                            borderRadius: "4px",
                            cursor: "pointer"
                        },
                        onclick: () => {
                            document.body.removeChild(overlay);
                            resolve('delete');
                        }
                    }),
                    $el("button", {
                        textContent: "Cancel",
                        style: {
                            padding: "8px 16px",
                            backgroundColor: "#6c757d",
                            color: "white",
                            border: "none",
                            borderRadius: "4px",
                            cursor: "pointer"
                        },
                        onclick: () => {
                            document.body.removeChild(overlay);
                            resolve(null);
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
                    zIndex: "10001"
                }
            }, [dialog]);
            
            document.body.appendChild(overlay);
        });
    }
    
    /**
     * Delete folder and move its contents to parent level
     */
    async deleteFolderAndMoveContents(folder) {
        try {
            // Determine parent folder ID
            const parentId = folder.parent_id; // This will be null for root-level folders
            
            // Move subprompts to parent folder
            if (folder.children && folder.children.length > 0) {
                for (const itemId of folder.children) {
                    const item = this.treeData.items[itemId];
                    if (item) {
                        const response = await api.fetchApi(`/prompt_companion/subprompts/${encodeURIComponent(item.id)}`, {
                            method: 'PUT',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                id: item.id,
                                name: item.name,
                                positive: item.positive || '',
                                negative: item.negative || '',
                                trigger_words: item.trigger_words || [],
                                order: item.order || ["attached"],
                                folder_id: parentId,
                                folder_path: "" // Keep empty for backward compatibility during transition
                            })
                        });
                        
                        if (!response.ok) {
                            console.error(`Failed to move subprompt ${item.id}`);
                        }
                    }
                }
            }
            
            // Move subfolders to parent level
            if (folder.subfolders && folder.subfolders.length > 0) {
                for (const subfolder of folder.subfolders) {
                    const response = await api.fetchApi(`/prompt_companion/folders/${encodeURIComponent(subfolder.id)}`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            id: subfolder.id,
                            name: subfolder.name,
                            parent_id: parentId
                        })
                    });
                    
                    if (!response.ok) {
                        console.error(`Failed to move subfolder ${subfolder.id}`);
                    }
                }
            }
            
            // Delete the empty folder
            if (!folder.id || folder.id === 'undefined' || folder.id === 'null') {
                console.error("Cannot delete folder: missing or invalid ID", folder);
                return false;
            }
            
            const response = await api.fetchApi(`/prompt_companion/folders/${encodeURIComponent(folder.id)}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                this.expandedFolders.delete(folder.id);
                await this.refreshTreePreservingState();
                return true;
            } else {
                const errorData = await response.json();
                console.error(`Failed to delete folder: ${errorData.error || 'Unknown error'}`);
                return false;
            }
        } catch (error) {
            console.error("Error during folder deletion and content moving:", error);
            return false;
        }
    }
    
    /**
     * Delete folder and all its contents (original behavior)
     */
    async deleteFolderAndAllContents(folder) {
        try {
            // Validate folder has ID
            if (!folder.id || folder.id === 'undefined' || folder.id === 'null') {
                console.error("TREE VIEW: Cannot delete folder - missing or invalid ID", folder);
                await this.showAlertDialog("Cannot delete folder: missing or invalid ID");
                return false;
            }
            
            const deleteUrl = `/prompt_companion/folders/${encodeURIComponent(folder.id)}`;
            
            const response = await api.fetchApi(deleteUrl, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                const result = await response.json();
                this.expandedFolders.delete(folder.id);
                await this.refreshTreePreservingState();
                return true;
            } else {
                const errorData = await response.json();
                console.error(`Failed to delete folder: ${errorData.error || 'Unknown error'}`);
                return false;
            }
        } catch (error) {
            console.error("Error deleting folder:", error);
            return false;
        }
    }
    
    async renameFolder(folder) {
        const newName = await this.showInputDialog("Enter new folder name:", folder.name);
        if (!newName || newName.trim() === folder.name) return;
        
        try {
            // Validate folder has ID
            if (!folder.id || folder.id === 'undefined' || folder.id === 'null') {
                console.error("Cannot rename folder: missing or invalid ID", folder);
                await this.showAlertDialog("Cannot rename folder: missing or invalid ID");
                return false;
            }
            
            const response = await api.fetchApi(`/prompt_companion/folders/${encodeURIComponent(folder.id)}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    id: folder.id,
                    name: newName.trim(),
                    parent_id: folder.parent_id
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                // Keep the same expanded state for the renamed folder
                await this.refreshTreePreservingState();
                return true;
            } else {
                const errorData = await response.json();
                console.error(`Failed to rename folder: ${errorData.error || 'Unknown error'}`);
                return false;
            }
        } catch (error) {
            console.error("Error renaming folder:", error);
            return false;
        }
    }
    
    handleKeyboard(event) {
        if (event.key === 'Delete' && this.selectedItems.size > 0) {
            // Delete selected items
            const selectedIds = Array.from(this.selectedItems);
            selectedIds.forEach(id => {
                const item = this.treeData.items[id];
                if (item) {
                    this.deleteSubprompt(item);
                }
            });
        } else if (event.key === 'F2' && this.selectedItems.size === 1) {
            // Rename selected item
            const id = Array.from(this.selectedItems)[0];
            const item = this.treeData.items[id];
            if (item) {
                this.editSubprompt(item);
            }
        }
    }
    
    selectItem(itemId) {
        this.selectedItems.clear();
        this.selectedItems.add(itemId);
        this.updateSelection();
        
        const item = this.treeData.items[itemId];
        if (item && this.onSelectionChange) {
            this.onSelectionChange(item);
        }
    }
    
    /**
     * Expand all folders in the tree
     */
    expandAll() {
        if (this.treeData && this.treeData.folders) {
            Object.keys(this.treeData.folders).forEach(folderId => {
                this.expandedFolders.add(folderId);
                if (this.treeData.folders[folderId]) {
                    this.treeData.folders[folderId].expanded = true;
                }
            });
            this.renderTree();
        }
    }
    
    /**
     * Collapse all folders in the tree
     */
    collapseAll() {
        this.expandedFolders.clear();
        if (this.treeData && this.treeData.folders) {
            Object.values(this.treeData.folders).forEach(folder => {
                folder.expanded = false;
            });
            this.renderTree();
        }
    }
    
    async refreshTree() {
        await this.loadTreeData();
    }
    
    /**
     * Refresh tree while preserving expanded folder state
     */
    async refreshTreePreservingState() {
        // Store current expanded state before refresh
        const currentExpandedFolders = new Set(this.expandedFolders);
        
        // Reload data without rendering (skip initial render to prevent conflicts)
        await this.loadTreeData(true);
        
        // Restore expanded state after reload
        this.expandedFolders = currentExpandedFolders;
        
        // Update folder objects with preserved expanded state
        if (this.treeData && this.treeData.folders) {
            Object.entries(this.treeData.folders).forEach(([folderId, folder]) => {
                folder.expanded = this.expandedFolders.has(folderId);
            });
        }
        
        // Re-render with preserved state
        this.renderTree();
    }
    
    showError(message) {
        this.treeContent.innerHTML = `
            <div class="prompt-companion-tree-error">
                <span>⚠️ ${message}</span>
                <button onclick="this.parentNode.parentNode.previousSibling.click()">Retry</button>
            </div>
        `;
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

// Tree view instance management
let treeView = null;

function initializePromptTreeView(containerId) {
    const container = typeof containerId === 'string' ?
        document.getElementById(containerId) : containerId;
    
    if (container) {
        // Preserve expanded folder state from existing tree view before creating new instance
        let preservedExpandedFolders = new Set();
        if (treeView && treeView.expandedFolders) {
            preservedExpandedFolders = new Set(treeView.expandedFolders);
        }
        
        // Create new tree view instance (handles cases where dialog is reopened with new DOM elements)
        treeView = new PromptTreeView(container);
        
        // Restore preserved expanded folder state
        if (preservedExpandedFolders.size > 0) {
            treeView.expandedFolders = preservedExpandedFolders;
        }
    }
    return treeView;
}

function getPromptTreeView() {
    return treeView;
}

function clearPromptTreeView() {
    treeView = null;
}

// Export functions for use by other components
window.PromptCompanion = window.PromptCompanion || {};
window.PromptCompanion.initializeTreeView = initializePromptTreeView;
window.PromptCompanion.getTreeView = getPromptTreeView;
window.PromptCompanion.clearTreeView = clearPromptTreeView;