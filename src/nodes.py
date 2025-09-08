import json
from inspect import cleandoc
import logging

from aiohttp import web
import folder_paths
from server import PromptServer

from .extension_config import CONFIG_PATH, PROMPT_ADDITIONS, PromptAddition, PromptGroup

routes = PromptServer.instance.routes


def send_addition_list():
    PromptServer.instance.send_sync(
        "prompt-companion.addition-list", PROMPT_ADDITIONS.prompt_additions_as_dict()
    )


def save_prompt_definitions():
    with open(CONFIG_PATH, "w") as f:
        json.dump(PROMPT_ADDITIONS.prompt_additions_as_dict(), f, indent=2)

    send_addition_list()


@routes.post("/prompt-companion/prompt-addition")
async def write_prompt_addition(request):
    prompt_addition_data = await request.json()

    try:
        PROMPT_ADDITIONS.create_or_update_prompt_addition(
            PromptAddition(
                prompt_addition_data["name"],
                prompt_addition_data.get("trigger_words", ""),
                prompt_addition_data.get("positive_prompt_addition_text", ""),
                prompt_addition_data.get("negative_prompt_addition_text", ""),
                prompt_addition_data.get("id"),
            )
        )
    except Exception as e:
        return web.json_response({"message": str(e)}, status=404)

    save_prompt_definitions()

    return web.json_response(PROMPT_ADDITIONS.prompt_additions_as_dict(), status=200)


@routes.get("/prompt-companion/prompt-addition")
async def get_prompt_additions(request):
    return web.json_response(PROMPT_ADDITIONS.prompt_additions_as_dict(), status=200)


@routes.delete("/prompt-companion/prompt-addition/{prompt_addition_name}")
async def delete_prompt_addition(request):
    try:
        PROMPT_ADDITIONS.delete_prompt_addition(
            request.match_info["prompt_addition_name"]
        )
    except Exception as e:
        return web.json_response({"message": str(e)}, status=404)

    save_prompt_definitions()

    return web.json_response(PROMPT_ADDITIONS.prompt_additions_as_dict(), status=200)


# Prompt Group API endpoints
@routes.post("/prompt-companion/prompt-group")
async def write_prompt_group(request):
    prompt_group_data = await request.json()

    try:
        PROMPT_ADDITIONS.create_or_update_prompt_group(
            PromptGroup(
                prompt_group_data["name"],
                prompt_group_data.get("trigger_words", []),
                prompt_group_data.get("additions", []),
                prompt_group_data.get("id"),
            )
        )
    except Exception as e:
        return web.json_response({"message": str(e)}, status=404)

    save_prompt_definitions()

    return web.json_response(PROMPT_ADDITIONS.prompt_additions_as_dict(), status=200)


@routes.get("/prompt-companion/prompt-group")
async def get_prompt_groups(request):
    return web.json_response(PROMPT_ADDITIONS.prompt_additions_as_dict(), status=200)


@routes.delete("/prompt-companion/prompt-group/{prompt_group_id}")
async def delete_prompt_group(request):
    group_id = int(request.match_info["prompt_group_id"])
    try:
        PROMPT_ADDITIONS.delete_prompt_group(group_id)
    except Exception as e:
        return web.json_response({"message": str(e)}, status=404)

    save_prompt_definitions()

    return web.json_response(PROMPT_ADDITIONS.prompt_additions_as_dict(), status=200)


class PromptCompanion:
    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("ckpt_name", "positive_combined_prompt", "negative_combined_prompt", "positive_addition", "negative_addition")
    FUNCTION = "combine_prompts"
    OUTPUT_NODE = True
    CATEGORY = "jfc"

    @classmethod
    def INPUT_TYPES(cls):
        addition_type_options = ["Individual", "Group"]
        group_mode_options = ["Manual", "Automatic (Trigger Words)"]
        
        return {
            "required": {
                "ckpt_name": (
                    folder_paths.get_filename_list("checkpoints"),
                    {"tooltip": "The name of the checkpoint (model) to load."},
                ),
                "addition_type": (addition_type_options, {"default": "Individual"}),
                "prompt_group_mode": (group_mode_options, {"default": "Manual"}),
                "combine_mode": (["prepend", "append"], {"default": "prepend"}),
                "enable_addition": ("BOOLEAN", {"default": "true"}),
                "prompt_addition_name": (
                    [""] + (list(PROMPT_ADDITIONS.prompt_additions.keys()) if PROMPT_ADDITIONS.prompt_additions else []),
                    {"default": ""}
                ),
                "prompt_addition_group": (
                    [""] + ([g.name for g in PROMPT_ADDITIONS.prompt_groups.values()] if PROMPT_ADDITIONS.prompt_groups else []),
                    {"default": ""}
                ),
                "positive_addition": (
                    "STRING",
                    {"multiline": True, "default": "", "dynamicPrompts": False},
                ),
                "negative_addition": (
                    "STRING",
                    {"multiline": True, "default": "", "dynamicPrompts": False},
                ),
                "positive_prompt": (
                    "STRING",
                    {"multiline": True, "default": "", "dynamicPrompts": False},
                ),
                "negative_prompt": (
                    "STRING",
                    {"multiline": True, "default": "", "dynamicPrompts": False},
                ),
            },
        }

    def combine_prompts(
        self,
        ckpt_name,
        addition_type,
        prompt_group_mode,
        combine_mode,
        enable_addition,
        prompt_addition_name,
        prompt_addition_group,
        positive_addition,
        negative_addition,
        positive_prompt,
        negative_prompt,
    ):
        # Always return ckpt_name first
        if not enable_addition:
            return (ckpt_name, positive_prompt, negative_prompt, "", "")

        # Calculate addition values based on type
        calculated_positive_addition = ""
        calculated_negative_addition = ""
        
        if addition_type == "Individual":
            # Individual mode - use the textbox values (which should contain selected addition)
            calculated_positive_addition = positive_addition
            calculated_negative_addition = negative_addition
                        
        elif addition_type == "Group":
            # Group mode - calculate from groups based on prompt_group_mode
            positive_additions = []
            negative_additions = []
            
            if prompt_group_mode == "Manual":
                # Manual mode - use the selected group only
                if prompt_addition_group:
                    selected_group = None
                    for group in PROMPT_ADDITIONS.prompt_groups.values():
                        if group.name == prompt_addition_group:
                            selected_group = group
                            break
                    
                    if selected_group:
                        # Get all additions in the selected group
                        for addition_ref in selected_group.additions:
                            addition_id = addition_ref.get('addition_id')
                            for addition in PROMPT_ADDITIONS.prompt_additions.values():
                                if addition.id == addition_id:
                                    if addition.positive_prompt_addition_text:
                                        positive_additions.append(addition.positive_prompt_addition_text)
                                    if addition.negative_prompt_addition_text:
                                        negative_additions.append(addition.negative_prompt_addition_text)
                                    break
                                    
            else:  # "Automatic (Trigger Words)"
                # Automatic mode - use trigger word matching (original logic)
                for group in PROMPT_ADDITIONS.prompt_groups.values():
                    # Check if any trigger words match in ckpt_name
                    trigger_match = False
                    for trigger_word in group.trigger_words:
                        if trigger_word.lower() in ckpt_name.lower():
                            trigger_match = True
                            break
                    
                    if trigger_match:
                        # Get all additions in this group and combine their prompts
                        for addition_ref in group.additions:
                            addition_id = addition_ref.get('addition_id')
                            for addition in PROMPT_ADDITIONS.prompt_additions.values():
                                if addition.id == addition_id:
                                    if addition.positive_prompt_addition_text:
                                        positive_additions.append(addition.positive_prompt_addition_text)
                                    if addition.negative_prompt_addition_text:
                                        negative_additions.append(addition.negative_prompt_addition_text)
                                    break
            
            # Combine all matching group additions
            calculated_positive_addition = ", ".join(positive_additions)
            calculated_negative_addition = ", ".join(negative_additions)

        # Combine additions with base prompts using combine_mode
        final_positive_combined = positive_prompt
        final_negative_combined = negative_prompt
        
        if calculated_positive_addition:
            if combine_mode == "prepend":
                final_positive_combined = f"{calculated_positive_addition}, {positive_prompt}".strip(", ")
            else:  # append
                final_positive_combined = f"{positive_prompt}, {calculated_positive_addition}".strip(", ")
        
        if calculated_negative_addition:
            if combine_mode == "prepend":
                final_negative_combined = f"{calculated_negative_addition}, {negative_prompt}".strip(", ")
            else:  # append
                final_negative_combined = f"{negative_prompt}, {calculated_negative_addition}".strip(", ")

        return (
            ckpt_name, 
            final_positive_combined, 
            final_negative_combined, 
            calculated_positive_addition, 
            calculated_negative_addition
        )


# A dictionary that contains all nodes you want to export with their names
# NOTE: names should be globally unique
NODE_CLASS_MAPPINGS = {"PromptCompanion": PromptCompanion}

# A dictionary that contains the friendly/humanly readable titles for the nodes
NODE_DISPLAY_NAME_MAPPINGS = {"PromptCompanion": "Prompt Companion"}
