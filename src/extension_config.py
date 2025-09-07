import json
import logging
import os
import os.path

import folder_paths
import jsonschema

comfy_path = os.path.dirname(folder_paths.__file__)
extension_path = os.path.join(os.path.dirname(__file__))

CONFIG_PATH = os.path.join(extension_path, "prompt-companion-config.json")
schema_path = os.path.join(extension_path, "config-schema.json")


class PromptAddition:
    name: str
    trigger_words: str
    trigger_words_list: list[str]
    prompt_addition_text: str
    prompt_addition_text_list: list[str]

    def __init__(
        self, name: str, trigger_words: str = "", prompt_addition_text: str = ""
    ):
        self.name = name
        self.trigger_words = trigger_words
        self.trigger_words_list = PromptAddition.raw_string_to_list(trigger_words)
        self.prompt_addition_text = prompt_addition_text
        self.prompt_addition_text_list = PromptAddition.raw_string_to_list(
            prompt_addition_text
        )

    def as_dict(self, include_lists: bool = False):
        self_dict: dict[str, str | list[str]] = {
            "name": self.name,
            "trigger_words": self.trigger_words,
            "prompt_addition_text": self.prompt_addition_text,
        }
        if include_lists:
            self_dict["trigger_words_list"] = self.trigger_words_list
            self_dict["prompt_addition_text_list"] = self.trigger_words_list

        return self_dict

    @staticmethod
    def raw_string_to_list(raw_string: str) -> list[str]:
        return list(map(lambda x: x.strip(), raw_string.split(",")))


class ExtensionConfig:
    _prompt_additions: dict[str, PromptAddition]

    def __init__(self, config_data: list[dict] = []):
        if config_data:
            with open(schema_path, "r") as schema_file:
                try:
                    jsonschema.validate(config_data, json.load(schema_file))
                except jsonschema.ValidationError as e:
                    logging.error(
                        "Config file failed to validated against expected schema!"
                    )

        self._prompt_additions = {}

        for prompt_addition in config_data:
            self._prompt_additions[prompt_addition["name"]] = PromptAddition(
                prompt_addition["name"],
                prompt_addition["trigger_words"],
                prompt_addition["prompt_addition_text"],
            )

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
        self._prompt_additions[prompt_addition.name] = prompt_addition

    def delete_prompt_addition(self, name):
        if name not in self._prompt_additions.keys():
            logging.error(f"Tried to delete non-existent prompt addition {name}")
            raise KeyError
        del self._prompt_additions[name]

    def prompt_additions_as_dict(self) -> list[dict[str, str | list[str]]]:
        return [
            prompt_addition.as_dict()
            for prompt_addition in self._prompt_additions.values()
        ]

    @property
    def prompt_additions(self) -> dict[str, PromptAddition]:
        return self._prompt_additions


config_data = []

if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, "r") as config_file:
        config_data = json.load(config_file)

PROMPT_ADDITIONS = ExtensionConfig(config_data)
