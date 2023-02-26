import re
import os
import atexit
import json
from enum import Enum
from functools import partial

'''
COMMON PITFALLS that cause bugs

removing the tag in a statement that selects entities with that tag

using 
execute as __
when you should be using
execute as __ at __


'''

MARKER_MOB = "minecraft:marker"
ABOVE = "~ ~1 ~"
update_files = []
folders_in_path = os.getcwd().split(os.sep)
try:
    DATAPACK_NAME = folders_in_path[folders_in_path.index("datapacks") + 1]
except ValueError:
    print("DATAPACKS FOLDER WAS NOT FOUND, ARE YOU AWARE YOU ARE NOT IN A DATAPACK FILE?")

class OutputFile:
    def __init__(self, file_no_ext, data=None, is_update_file=False) -> None:
        self.file_name = f"{file_no_ext}"
        self.file_name_with_ext = f"{file_no_ext}.mcfunction"
        self.lines = [] if data is None else data
        self.variants = []
        if is_update_file:
            update_files.append(file_no_ext)
            atexit.register(add_update_files)
        atexit.register(self.write_to_file)

    def append(self, line):
        self.lines.append(line)
    
    def add_variant(self, suffix):
        self.variants.append(OutputFile(f"{self.file_name}{suffix}"))

    def get_variant(self, index) -> 'OutputFile':
        return self.variants[index]
        
    def extend(self, *lines):
        for line in lines:
            self.lines.extend(line)
    
    def write_to_file(self):
        # print(self.lines)
        with open(self.file_name_with_ext, 'w') as f:
            try:
                print("\n".join(self.lines), file=f)
            except TypeError:
                print("======Error with", self.file_name, "======")
                print(self.lines)


UPDATE_JSON_FILE = None
def add_update_files():
    global UPDATE_JSON_FILE
    # print(UPDATE_JSON_FILE)
    with open(UPDATE_JSON_FILE, 'r') as f:
        original = f.read()
    # print(original)
    original = json.loads(original)
    new_values = original["values"]
    with open(UPDATE_JSON_FILE, 'w') as f:
        for function in update_files:
            if (cur:=f"{DATAPACK_NAME}:{DATAPACK_NAME}/{function}") not in new_values:
                new_values.append(cur)
        original["values"] = new_values
        output = json.dumps(original, indent=4)
        # print(output)
        f.write(output)

has_made_scoreboard_file = False
scoreboard_creation_template = "scoreboard objectives add {} dummy"
scoreboard_set_value_template = "scoreboard players set {} {} {}"
GLOBAL_VAR_HOLDER = 'global'
CONST_SCOREBOARD_NAME = 'const'
scoreboard_variables_created = set()

reset = OutputFile("reset")
reset.append("say Reload has completed")
reset.append(f"scoreboard objectives add {CONST_SCOREBOARD_NAME} dummy")

REMAINDER_SCOREBOARD_OBJECTIVE = "remainder"
reset.append(f"scoreboard objectives add {REMAINDER_SCOREBOARD_OBJECTIVE} dummy")

helper_update = OutputFile("helper_update", is_update_file=True)


def call_function(function_name:OutputFile | str, delay=0, unit='t'):
    if type(function_name) is OutputFile:
        function_part = f"function {DATAPACK_NAME}:{DATAPACK_NAME}/{function_name.file_name}"
    else:
        function_part = f"function {DATAPACK_NAME}:{DATAPACK_NAME}/{function_name}"
    if delay > 0:
        return [f"schedule {function_part} {convert_to_ticks(delay, unit)}"]
    return [function_part]

def play_sound_at_pitches_based_on_score(counting_score, sound_name, cooldown_values, pitches):
    return [
        execute_if_score_equals(counting_score, score,
            playsound(sound_name, pitch)
        )[0]
        for score, pitch in zip(cooldown_values, pitches)
    ]     

def checkerboard_pattern(block1 : str, block2 : str, lower_x, lower_y, upper_x, upper_y):
    _, block1_name = block1.split(":")
    _, block2_name = block2.split(":")
    cur_checkerboard = OutputFile(f"checkerboard_{block1_name}_{block2_name}")
    for y in range(lower_y, upper_y + 1):
        for x in range(lower_x, upper_x + 1):
            to_place = block1 if (x + y) % 2 == 0 else block2
            cur_checkerboard.append(f"setblock {x} ~ {y} {to_place}")
    cur_checkerboard.write_to_file()

def get_remainder(large_value : int | str, divisor: int | str, score_to_save_to:str, 
                    large_value_owner=GLOBAL_VAR_HOLDER, 
                    score_to_save_to_owner: str=GLOBAL_VAR_HOLDER,
                    divisor_owner: str=GLOBAL_VAR_HOLDER,
                    ):
    '''scoreboards or actual numbers can be used for large_value
    or divisor. If actual numbers are used, they will automatically
    be converted to consts
    '''
    divisor_part = f"{divisor_owner} {divisor}"
    if type(divisor) is int:
        divisor_part = const_wrapper(divisor)

    large_value_part = f"{large_value_owner} {large_value}"
    if type(large_value) is int:
        large_value_part = const_wrapper(large_value)

    return [
        f"scoreboard players operation {score_to_save_to_owner} {score_to_save_to} = {large_value_part}",
        f"scoreboard players operation {score_to_save_to_owner} {score_to_save_to} %= {divisor_part}",
    ]

def convert_to_ticks(value: int, unit: str):
    conversion = {
        "t" : 1,
        "s" : 20,
        "m" : 1200
    }
    return value*conversion[unit]
def add_delay(delay: int, tag: str, unit="t"):
    return ['summon area_effect_cloud ~ ~ ~ {Tags:["'f'{tag}"],Age:'+f"-{convert_to_ticks(delay, unit)}}}"]

def run_when_tag_gone(tag, to_run):
    return execute_unless(f"entity @e[type=area_effect_cloud,tag={tag}]", to_run)
allow_after_delay = run_when_tag_gone

def execute_if_divisible(scoreboard_name: int | str, divisor: int | str, wanted_remainder: int, to_run : list, if_or_unless: str="if"):
    rem_saved_to_owner = f"remainder_of_{scoreboard_name}_mod_{divisor}"
    return get_remainder(scoreboard_name, divisor, REMAINDER_SCOREBOARD_OBJECTIVE, score_to_save_to_owner=rem_saved_to_owner) +\
        convert_from_single_as_needed(f"execute {if_or_unless} score {rem_saved_to_owner} {REMAINDER_SCOREBOARD_OBJECTIVE} matches {wanted_remainder} run", to_run)

def create_const(value):
    write_scoreboard_line(f"scoreboard players set const{value} const {value}")

def scoreboard_operation(score1, op, score2: int | str, owner1=GLOBAL_VAR_HOLDER, owner2=GLOBAL_VAR_HOLDER):
    second_part = f"{owner2} {score2}"
    if type(score2) is int:
        second_part = const_wrapper(score2)
    create_scoreboard(score1, 0, owner1)
    return [f"scoreboard players operation {owner1} {score1} {op} {second_part}"]

operation = scoreboard_operation
def increment(score):
    return scoreboard_operation(score, '+=', 1)

def raw(text: str):
    return [line.strip() for line in text.strip().splitlines()]

def tuple_to_relative_string(tup):
    return f"~{tup[0]} ~{tup[1]} ~{tup[2]}"

def tuple_to_string(tup):
    return " ".join(str(x) for x in tup)

def execute_at(pos : str | tuple[int, int, int], to_run : list):
    if type(pos) == tuple:
        pos = tuple_to_string(pos)
    return [f"execute positioned {pos} run {command}" for command in to_run]

execute_positioned = execute_at

def execute_if(condition : str, to_run : list):
    return convert_from_single_as_needed(f"execute if {condition} run", to_run)

def execute_if_score(scoreboard_name : str, check: str, to_run : list, if_or_unless: str="if", owner=GLOBAL_VAR_HOLDER):
    create_scoreboard_as_needed(scoreboard_name)
    return convert_from_single_as_needed(f"execute {if_or_unless} score {owner} {scoreboard_name} {check} run", to_run)

execute_unless_score = partial(execute_if_score, if_or_unless="unless")

def execute_if_score_equals(scoreboard_name : str, value: int, to_run : list):
    create_scoreboard(scoreboard_name)
    return convert_from_single_as_needed(f"execute if score {GLOBAL_VAR_HOLDER} {scoreboard_name} matches {value} run", to_run)
execute_if_score_matches = execute_if_score_equals
def execute_if_score_other_score(score1 : str, op: str, score2: str, to_run : list, owner1: str=GLOBAL_VAR_HOLDER, owner2: str=GLOBAL_VAR_HOLDER):
    create_scoreboard_as_needed(score1)
    return convert_from_single_as_needed(f"execute if score {owner1} {score1} {op} {owner2} {score2} run", to_run)

def execute_if_score_equals_score(score1 : str, score2: str, to_run : list, owner1: str=GLOBAL_VAR_HOLDER, owner2: str=GLOBAL_VAR_HOLDER):
    return execute_if_score_other_score(score1, '=', score2, to_run, owner1, owner2)
def execute_unless(condition : str, to_run : list):
    return convert_from_single_as_needed(f"execute unless {condition} run", to_run)

def store_scores(selector: str, scoreboard_and_nbt: list[tuple[str, str]]):
    return [f"execute store result score {selector} {scoreboard_name} run data get entity @s {nbt_path}" for scoreboard_name, nbt_path in scoreboard_and_nbt]

def store_count_entity_score(scoreboard_name: str, entity_selector: str, score_owner=GLOBAL_VAR_HOLDER):
    create_scoreboard_as_needed(scoreboard_name)
    return [f"execute store result score {score_owner} {scoreboard_name} run execute if entity {entity_selector}"]

def set_score_from(scoreboard_name: str, get_score_from: str, owner: str=GLOBAL_VAR_HOLDER):
    create_scoreboard_as_needed(scoreboard_name)
    return f"execute store result score {owner} {scoreboard_name} {get_score_from}"

def set_score_from_other_score(score_to_set: str, other_score: str, owner: str=GLOBAL_VAR_HOLDER, owner2: str=GLOBAL_VAR_HOLDER):
    create_scoreboard_as_needed(score_to_set)
    return [f"execute store result score {owner} {score_to_set} run scoreboard players get {owner2} {other_score}"]
    

def set_score(scoreboard_name: str, value: str | int, owner: str=GLOBAL_VAR_HOLDER):
    create_scoreboard_as_needed(scoreboard_name)
    return [f"scoreboard players set {owner} {scoreboard_name} {value}"]

def convert_from_single_as_needed(prefix:str, to_run: str | list):
    if type(to_run) == str:
        return [f"{prefix} {to_run}"]
    before = to_run.copy()
    to_run.sort(key=lambda x: x.startswith("tag"))
    # if to_run != before:
        # print("NOTE: order was changed")
        # print("before:")
        # print("\n".join(before))
        # print("after:")
        # print("\n".join(to_run))
    return [f"{prefix} {command[0] if type(command) is list else command}" for command in to_run]

def create_scoreboard_as_needed(scoreboard_name: str):
    if scoreboard_name not in scoreboard_variables_created:
        scoreboard_variables_created.add(scoreboard_name)
        reset.append(f"scoreboard objectives add {scoreboard_name} dummy")

def execute_as(selector : str, to_run : list):
    return convert_from_single_as_needed(f"execute as {selector} run", to_run)


def execute_as_at_self(selector : str, to_run : list):
    return convert_from_single_as_needed(f"execute as {selector} at @s run", to_run)

execute_as_at = execute_as_at_self

def playsound(sound_name: str, pitch : float=1, to_play_sound_to_selector: str="@a at @s", volume:float=1):
    return execute_as(to_play_sound_to_selector, 
        [f"playsound {sound_name} master @s ~ ~ ~ {volume} {pitch}"]
    )

def element_wise(a, b):
    return tuple(x + y for x, y in zip(a, b))

def place_marker(pos:str="~ ~ ~", tags:list[str]=None):
    if tags is None:
        tags = []
    return [f"summon marker {pos}" + " {Tags:" + format_tags_for_nbt(tags) + "}"]
summon_marker = place_marker

def tp(from_, to_):
    return [f"tp {from_} {to_}"]

def say(to_say:str):
    return [f"say {to_say}"]

def debug(to_say):
    return tellraw("DEBUG") + tellraw(to_say)
    
def get_correct_formatting(to_say):
    return to_say if "{" in to_say else f'"{to_say}"'
    
    
def tellraw(to_say:str, selector='@a'):
    to_say = get_correct_formatting(to_say)
    return [f'tellraw {selector} {to_say}']
announce = tellraw

def title(text, selector='@a', spot='title'):
    text = get_correct_formatting(text)
    return [f'title {selector} {spot} {text}']

def title_and_chat(formatted_text, selector='@a', title_spot='title'):
    return title(formatted_text, selector, title_spot) + tellraw(formatted_text, selector)
    
def format_text(text=None,
                selector=None,
                separator=None,
                bold=False,
                italic=False,
                underlined=False,
                strikethrough=False,
                obfuscated=False):
    '''note, either text or selector can be given, but not both. If a selector is chosen, then the separator can be used.'''
    ret = {}
    options_given = (locals()).copy()
    for option, value in options_given.items():
        if value:
            to_use = str(value).lower()
            if option == 'text':
                to_use = value
            ret[option] = to_use
    return ret


def negate(to_negate):
    return f"!{to_negate}"

get_type = type
def selector_entity(tag=None, tags=None, negative_tags=None, 
                    limit=None,type=None,dx=None,dy=None,dz=None, 
                    distance=None, sort=None, team=None,
                    score=None, scores=None, selector='@e'):
    # multiple_values_allowed = ["tags"]
    # special = ["negative_tags"]
    to_go_over = list(locals().items())
    # print(to_go_over)
    ret = []
    for keyword, potential_value in to_go_over:
        # print(keyword, potential_value)
        if potential_value is None or keyword == 'selector':
            continue
        if keyword == 'tags':
            keyword = keyword.removesuffix("s")
        if keyword == 'score':
            keyword += 's'
        if get_type(potential_value) is list:
            if keyword == 'scores':
                desired_values = [f"{scoreboard}={value}" for scoreboard, value in potential_value]
                ret.append(f"{keyword}={{{','.join(desired_values)}}}")
            else:
                ret.extend(f"{keyword}={value}" for value in potential_value)
        else:
            ret.append(f"{keyword}={potential_value}")
    combined = ','.join(ret)
    return f"{selector}[{combined}]" if combined else f"{selector}"

entity_selector = selector_entity
at_e = selector_entity
at_a = partial(selector_entity, selector='@a')
at_s = partial(selector_entity, selector='@s')

def output_commands(file, commands):
    print("\n".join(commands), file=file)

def write_scoreboard_line(mc_function_line):
    reset.append(mc_function_line)

def write_scoreboard_lines(mc_function_lines):
    reset.extend(mc_function_lines)

def increment_each_tick(scoreboard_name, selector=GLOBAL_VAR_HOLDER):
    helper_update.append(f"scoreboard players add {selector} {scoreboard_name} 1")

def create_scoreboard(scoreboard_name: str, val=None, holder=GLOBAL_VAR_HOLDER):
    create_scoreboard_as_needed(scoreboard_name)
    # if scoreboard_name not in scoreboard_variables_created:
    if val is not None:
        write_scoreboard_line(scoreboard_set_value_template.format(holder, scoreboard_name, val))

def set_score_to_count_of(scoreboard, selector_to_count, 
                        scoreboard_owner=GLOBAL_VAR_HOLDER):
    return [set_score_from(scoreboard, f"if entity {selector_to_count}", scoreboard_owner)]

def add_tag(selector: str, tag_name: str):
    return [f"tag {selector} add {tag_name}"]

tag_add = add_tag

def format_tags_for_nbt(tags : list[str]):
    return f"{[str(x) for x in tags]}".replace("'", '"')

def kill(selector: str):
    return [f"kill {selector}"]

def remove_tag(selector: str, tag_name: str):
    return [f"tag {selector} remove {tag_name}"]

def smooth_remove(selector: str):
    return [
        f"tp {selector} ~ ~-200 ~",
        f"kill {selector}"
    ]



def const_wrapper(value: int):
    const_holder = f"{CONST_SCOREBOARD_NAME}{value}"
    write_scoreboard_lines(set_score(CONST_SCOREBOARD_NAME, value, owner=const_holder))
    return f"{const_holder} {CONST_SCOREBOARD_NAME}"

def create_const_value_scoreboard(value: int):
    const_holder = f"const{value}"
    return set_score(CONST_SCOREBOARD_NAME, value, const_holder)

def eval_macro(line : str):
    var, op, value = re.search(r"([a-z\d_]+) ?([^a-z\d]+) ?(\d+)", line).groups()
    var = var.strip()
    op = op.strip()
    value = value.strip()
    # print(var, op, value)
    if op == "=":
        return set_score(var, value)
    const_holder = f"const{value}"
    create_scoreboard(CONST_SCOREBOARD_NAME, value, const_holder)
    return [f"scoreboard players operation {GLOBAL_VAR_HOLDER} {var} {op} {const_holder} {CONST_SCOREBOARD_NAME}"]
macro = eval_macro


def reset_extras():
    for i in range(16):
        create_const(i)

reset_extras()