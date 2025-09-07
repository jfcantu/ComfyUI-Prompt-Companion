import json
from inspect import cleandoc
import logging

from aiohttp import web
from server import PromptServer

from .extension_config import CONFIG_PATH, PROMPT_ADDITIONS, PromptAddition

routes = PromptServer.instance.routes


def send_addition_list():
    print(f"sending {PROMPT_ADDITIONS.prompt_additions_as_dict()}")

    PromptServer.instance.send_sync(
        "prompt-companion.addition-list", PROMPT_ADDITIONS.prompt_additions_as_dict()
    )


def save_prompt_definitions():
    with open(CONFIG_PATH, "w") as f:
        json.dump(PROMPT_ADDITIONS.prompt_additions_as_dict(), f)

    send_addition_list()


@routes.post("/prompt-companion/prompt-addition")
async def write_prompt_addition(request):
    prompt_addition_data = await request.json()

    try:
        print(f"saving prompt data: {prompt_addition_data}")
        PROMPT_ADDITIONS.create_or_update_prompt_addition(
            PromptAddition(
                prompt_addition_data["name"],
                prompt_addition_data["trigger_words"],
                prompt_addition_data["prompt_addition_text"],
            )
        )
    except Exception as e:
        return web.json_response({"message": str(e)}, status=404)

    save_prompt_definitions()

    print(f"saved prompt definitions")

    print(PROMPT_ADDITIONS.prompt_additions_as_dict())

    return web.json_response(PROMPT_ADDITIONS.prompt_additions_as_dict(), status=200)


@routes.get("/prompt-companion/prompt-addition")
async def get_prompt_additions(request):
    return web.json_response(PROMPT_ADDITIONS.prompt_additions_as_dict(), status=200)


@routes.delete("/prompt-companion/prompt-addition/{prompt_addition_name}")
async def delete_prompt_addition(request):
    print(f"{request.match_info['prompt_addition_name']}")
    try:
        PROMPT_ADDITIONS.delete_prompt_addition(
            request.match_info["prompt_addition_name"]
        )
    except Exception as e:
        return web.json_response({"message": str(e)}, status=404)

    save_prompt_definitions()

    return web.json_response(PROMPT_ADDITIONS.prompt_additions_as_dict(), status=200)


class PromptCompanion:
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("prompt_text",)
    FUNCTION = "combine_prompts"
    OUTPUT_NODE = True
    CATEGORY = "jfc"

    @classmethod
    def INPUT_TYPES(cls):
        print(f"addition names: {list(PROMPT_ADDITIONS.prompt_additions.keys())}")

        return {
            "required": {
                "prompt_addition_name": (
                    list(PROMPT_ADDITIONS.prompt_additions.keys()),
                ),
                "combine_mode": (["prepend", "append"], {"default": "prepend"}),
                "enable_addition": ("BOOLEAN", {"default": "true"}),
            },
            "optional": {
                "prompt_addition_text": (
                    "STRING",
                    {"multiline": "true", "default": ""},
                ),
                "prompt_text": (
                    "STRING",
                    {"multiline": "true", "default": ""},
                ),
                # implement later
                # "prompt_addition_trigger_words": (
                #     "STRING",
                #     {"multiline": "true", "default": ""},
                # ),
            },
        }

    def combine_prompts(
        self,
        prompt_addition_name,
        combine_mode,
        enable_addition,
        prompt_addition_text="",
        prompt_text="",
        # implement later
        # prompt_addition_trigger_words="",
    ):
        if not enable_addition:
            return (prompt_text,)

        if combine_mode == "prepend":
            combination_order = [prompt_addition_text, prompt_text]
        elif combine_mode == "append":
            combination_order = [prompt_text, prompt_addition_text]
        else:
            logging.error("Somehow received an invalid combine_mode")
            raise Exception("Somehow received an invalid combine_mode")

        combined_text = ", ".join(combination_order)
        return (combined_text,)


# A dictionary that contains all nodes you want to export with their names
# NOTE: names should be globally unique
NODE_CLASS_MAPPINGS = {"PromptCompanion": PromptCompanion}

# A dictionary that contains the friendly/humanly readable titles for the nodes
NODE_DISPLAY_NAME_MAPPINGS = {"PromptCompanion": "Prompt Companion"}
