import json
import logging
import os
import os.path

import folder_paths
import jsonschema

comfy_path = os.path.dirname(folder_paths.__file__)
extension_path = os.path.join(os.path.dirname(__file__))
user_directory = folder_paths.get_user_directory()

# Store config in user directory instead of extension directory
CONFIG_PATH = os.path.join(user_directory, "prompt-companion-config.json")
schema_path = os.path.join(extension_path, "config-schema.json")


class PromptAddition:
    id: int | None
    name: str
    trigger_words: str
    trigger_words_list: list[str]
    positive_prompt_addition_text: str
    positive_prompt_addition_text_list: list[str]
    negative_prompt_addition_text: str
    negative_prompt_addition_text_list: list[str]

    def __init__(
        self, name: str, trigger_words: str = "", positive_prompt_addition_text: str = "", negative_prompt_addition_text: str = "", id: int | None = None
    ):
        self.id = id
        self.name = name
        self.trigger_words = trigger_words
        self.trigger_words_list = PromptAddition.raw_string_to_list(trigger_words)
        self.positive_prompt_addition_text = positive_prompt_addition_text
        self.positive_prompt_addition_text_list = PromptAddition.raw_string_to_list(
            positive_prompt_addition_text
        )
        self.negative_prompt_addition_text = negative_prompt_addition_text
        self.negative_prompt_addition_text_list = PromptAddition.raw_string_to_list(
            negative_prompt_addition_text
        )

    def as_dict(self, include_lists: bool = False):
        self_dict: dict[str, str | list[str] | int | None] = {
            "id": self.id,
            "name": self.name,
            "trigger_words": self.trigger_words,
            "positive_prompt_addition_text": self.positive_prompt_addition_text,
            "negative_prompt_addition_text": self.negative_prompt_addition_text,
        }
        if include_lists:
            self_dict["trigger_words_list"] = self.trigger_words_list
            self_dict["positive_prompt_addition_text_list"] = self.positive_prompt_addition_text_list
            self_dict["negative_prompt_addition_text_list"] = self.negative_prompt_addition_text_list

        return self_dict

    @staticmethod
    def raw_string_to_list(raw_string: str) -> list[str]:
        return list(map(lambda x: x.strip(), raw_string.split(",")))


class PromptGroup:
    id: int | None
    name: str
    trigger_words: list[str]
    additions: list[dict[str, int]]

    def __init__(
        self, name: str, trigger_words: list[str] | None = None, additions: list[dict[str, int]] | None = None, id: int | None = None
    ):
        self.id = id
        self.name = name
        self.trigger_words = trigger_words or []
        self.additions = additions or []

    def as_dict(self) -> dict[str, str | list[str] | list[dict[str, int]] | int | None]:
        return {
            "id": self.id,
            "name": self.name,
            "trigger_words": self.trigger_words,
            "additions": self.additions,
        }


class ExtensionConfig:
    _prompt_additions: dict[str, PromptAddition]
    _prompt_groups: dict[int, PromptGroup]
    _next_addition_id: int
    _next_group_id: int

    def __init__(self, config_data: dict | list = {}):
        if config_data:
            with open(schema_path, "r") as schema_file:
                try:
                    jsonschema.validate(config_data, json.load(schema_file))
                except jsonschema.ValidationError as e:
                    logging.error(
                        "Config file failed to validate against expected schema!"
                    )

        self._prompt_additions = {}
        self._prompt_groups = {}
        
        # Handle backward compatibility - if config_data is a list, convert it
        if isinstance(config_data, list):
            config_data = {"prompt_additions": config_data, "prompt_groups": []}
        
        # Ensure the expected structure exists
        if "prompt_additions" not in config_data:
            config_data["prompt_additions"] = []
        if "prompt_groups" not in config_data:
            config_data["prompt_groups"] = []

        # Load prompt additions
        for prompt_addition in config_data["prompt_additions"]:
            addition_id = prompt_addition.get("id")
            if addition_id is None:
                # Auto-generate ID for old data without IDs
                addition_id = self._generate_next_addition_id(config_data["prompt_additions"])
                prompt_addition["id"] = addition_id
                
            # Handle backward compatibility for field name changes
            positive_text = prompt_addition.get("positive_prompt_addition_text", "")
            if not positive_text and "prompt_addition_text" in prompt_addition:
                positive_text = prompt_addition["prompt_addition_text"]
                
            self._prompt_additions[prompt_addition["name"]] = PromptAddition(
                prompt_addition["name"],
                prompt_addition.get("trigger_words", ""),
                positive_text,
                prompt_addition.get("negative_prompt_addition_text", ""),
                addition_id
            )
        
        # Load prompt groups
        for group in config_data["prompt_groups"]:
            group_id = group.get("id")
            if group_id is None:
                # Auto-generate ID for old data without IDs
                group_id = self._generate_next_group_id(config_data["prompt_groups"])
                group["id"] = group_id
                
            self._prompt_groups[group_id] = PromptGroup(
                group["name"],
                group.get("trigger_words", []),
                group.get("additions", []),
                group_id
            )
            
        # Set next ID counters
        self._next_addition_id = self._calculate_next_id([a.id for a in self._prompt_additions.values()])
        self._next_group_id = self._calculate_next_id(list(self._prompt_groups.keys()))

    def _generate_next_addition_id(self, additions_list):
        existing_ids = [a.get("id", 0) for a in additions_list if a.get("id") is not None]
        return max(existing_ids, default=0) + 1
    
    def _generate_next_group_id(self, groups_list):
        existing_ids = [g.get("id", 0) for g in groups_list if g.get("id") is not None]
        return max(existing_ids, default=0) + 1
    
    def _calculate_next_id(self, existing_ids):
        return max(existing_ids, default=0) + 1

    def create_prompt_addition(self, prompt_addition: PromptAddition):
        if prompt_addition.name in self._prompt_additions.keys():
            logging.error(
                f"Tried to create already-existing prompt addition {prompt_addition.name}"
            )
            raise KeyError
        self.create_or_update_prompt_addition(prompt_addition)

    def get_prompt_addition(self, name) -> PromptAddition:
        return self._prompt_additions[name]

    def update_prompt_addition(self, prompt_addition: PromptAddition):
        if prompt_addition.name not in self._prompt_additions.keys():
            logging.error(
                f"Tried to update non-existing prompt addition {prompt_addition.name}"
            )
            raise KeyError
        self.create_or_update_prompt_addition(prompt_addition)

    def create_or_update_prompt_addition(self, prompt_addition: PromptAddition):
        # Assign ID if creating new addition
        if prompt_addition.id is None:
            prompt_addition.id = self._next_addition_id
            self._next_addition_id += 1
        self._prompt_additions[prompt_addition.name] = prompt_addition

    def delete_prompt_addition(self, name):
        if name not in self._prompt_additions.keys():
            logging.error(f"Tried to delete non-existent prompt addition {name}")
            raise KeyError
        del self._prompt_additions[name]

    def prompt_additions_as_dict(self) -> dict:
        """Return the complete config data including prompt_additions and prompt_groups"""
        return {
            "prompt_additions": [
                prompt_addition.as_dict()
                for prompt_addition in self._prompt_additions.values()
            ],
            "prompt_groups": [
                prompt_group.as_dict()
                for prompt_group in self._prompt_groups.values()
            ]
        }
    
    def prompt_additions_list(self) -> list[dict[str, str | list[str] | int | None]]:
        """Return just the prompt additions as a list (for backward compatibility)"""
        return [
            prompt_addition.as_dict()
            for prompt_addition in self._prompt_additions.values()
        ]

    # Prompt group operations
    def create_prompt_group(self, prompt_group: PromptGroup):
        if any(g.name == prompt_group.name for g in self._prompt_groups.values()):
            logging.error(
                f"Tried to create already-existing prompt group {prompt_group.name}"
            )
            raise KeyError
        self.create_or_update_prompt_group(prompt_group)

    def get_prompt_group(self, group_id: int) -> PromptGroup:
        return self._prompt_groups[group_id]

    def update_prompt_group(self, prompt_group: PromptGroup):
        if prompt_group.id not in self._prompt_groups.keys():
            logging.error(
                f"Tried to update non-existing prompt group {prompt_group.name}"
            )
            raise KeyError
        self.create_or_update_prompt_group(prompt_group)

    def create_or_update_prompt_group(self, prompt_group: PromptGroup):
        # Assign ID if creating new group
        if prompt_group.id is None:
            prompt_group.id = self._next_group_id
            self._next_group_id += 1
        self._prompt_groups[prompt_group.id] = prompt_group

    def delete_prompt_group(self, group_id: int):
        if group_id not in self._prompt_groups.keys():
            logging.error(f"Tried to delete non-existent prompt group with ID {group_id}")
            raise KeyError
        del self._prompt_groups[group_id]

    @property
    def prompt_additions(self) -> dict[str, PromptAddition]:
        return self._prompt_additions
    
    @property
    def prompt_groups(self) -> dict[int, PromptGroup]:
        return self._prompt_groups


config_data = []

# Load config from user directory only
if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, "r") as config_file:
        config_data = json.load(config_file)
        print(f"[ComfyUI-Prompt-Companion] Loaded config from: {CONFIG_PATH}")
else:
    print(f"[ComfyUI-Prompt-Companion] No existing config found, will create new config at: {CONFIG_PATH}")

PROMPT_ADDITIONS = ExtensionConfig(config_data)
