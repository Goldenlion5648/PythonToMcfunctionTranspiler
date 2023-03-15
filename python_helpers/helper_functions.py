import re
import os
import atexit
import json
import sys
from enum import Enum
from functools import partial
import itertools as it
import operator as op
import shutil

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
BELOW = "~ ~-1 ~"
AIR = "air"
CUR_POS = "~ ~ ~"
SELF_POS = CUR_POS
HERE = CUR_POS
update_files = []
folders_in_path = os.getcwd().split(os.sep)
try:
    DATAPACK_NAME = folders_in_path[folders_in_path.index("datapacks") + 1]
except ValueError:
    print("DATAPACKS FOLDER WAS NOT FOUND, ARE YOU AWARE YOU ARE NOT IN A DATAPACK FILE?")
    exit()

DATAPACK_FOLDER_PREFIX = f"{DATAPACK_NAME}:{DATAPACK_NAME}/"

# remove old files
files = os.listdir()
if "helper_functions.py" in files:
    print("\n\nYou ran the wrong file\n\n")
    exit()
for file in files:
    if file.endswith(".mcfunction"):
        # print(file)
        os.remove(file)
    if os.path.isdir(file) and all(x.endswith(".mcfunction") for x in os.listdir(file)):
        shutil.rmtree(file)
        # exit()

class OutputFile:
    def __init__(self, file_no_ext, data=None, is_update_file=False, folder="", force_unqiue_lines=False) -> None:
        self.file_name = f"{file_no_ext}"
        self.file_name_with_ext = f"{file_no_ext}.mcfunction"
        self.lines = [] if data is None else data
        self.variants: list[OutputFile]= []
        self.folder = folder
        self.force_unqiue_lines = force_unqiue_lines
        if self.folder and not self.folder.endswith("/"):
            self.folder += '/'
        self.path_in_datapack = f"{self.folder}{self.file_name}"
        self.folder_and_extension = f"{self.folder}{self.file_name_with_ext}"
        self.path_with_datapack_name = f"{DATAPACK_FOLDER_PREFIX}{self.path_in_datapack}"
        self.path_with_datapack_name_and_extension = f"{DATAPACK_FOLDER_PREFIX}{self.folder_and_extension}"
        if is_update_file:
            update_files.append(file_no_ext)
            atexit.register(add_update_files)
        atexit.register(self.write_to_file)
    @property
    def content(self):
        return "\n".join(self.lines)

    def append(self, line):
        self.lines.append(line)
                
    def extend(self, *lines):
        for line in lines:
            self.lines.extend(line)

    def filter_unique_lines(self):
        seen = set()
        new_lines = []
        for line in self.lines:
            if line in seen:
                continue
            seen.add(line)
            new_lines.append(line)
        self.lines = new_lines
    
    def add_variant(self, suffix=''):
        if not suffix:
            suffix = len(self.variants)
        self.variants.append(OutputFile(f"{self.file_name}{suffix}", folder=self.folder))
        return self.variants[-1]

    def pop_variant(self):
        self.variants.pop()

    def get_variant(self, index) -> 'OutputFile':
        return self.variants[index]

    
    def write_to_file(self):
        # print(self.lines)
        file_to_make = self.folder_and_extension
        # print(file_to_make)
        folder_to_make = os.path.dirname(file_to_make)
        if folder_to_make:
            os.makedirs(folder_to_make, exist_ok=True)
        
        if self.force_unqiue_lines:
            self.filter_unique_lines()

        with open(file_to_make, 'w') as f:
            try:
                print(self.content, file=f)
            except TypeError:
                print("======Error with", self.file_name, "======")
                print(self.lines)
class BlockTag:
    def __init__(self, tag_name, *blocks) -> None:
        self.tag_name = tag_name
        self.blocks = []
        # print(blocks)
        if type(blocks[0]) == list:
            blocks = blocks[0] 
        self.extend(blocks)
        atexit.register(self.write_to_file)
    def append(self, block):
        self.blocks.append(block)
                
    def extend(self, *blocks):
        for block in blocks:
            self.blocks.extend(block)
    @property
    def content(self):
        return "\n".join(self.blocks)

    def __str__(self) -> str:
        return f"#{DATAPACK_NAME}:{self.tag_name}"

    def write_to_file(self):
        # print(self.lines)

        # return
        # print(sys.path)
        # exit()
        # tag_file_path = os.path.join(os.sep.join(os.getcwd().split(os.sep)[:-2]),  "tags","blocks",f"{self.tag_name}.json")
        up2 = os.path.dirname(os.path.dirname(os.getcwd()))
        # print(up2)
        tag_path = os.path.join(up2, "tags","blocks")
        # os.path.relpath()
        # print(tag_file_path)
        # exit()

        # file_to_make = self.folder_and_extension
        # folder_to_make = os.path.dirname(file_to_make)
        # if folder_to_make:
        os.makedirs(tag_path, exist_ok=True)
        tag_file = os.path.join(tag_path, f"{self.tag_name}.json")
        # if self.force_unqiue_lines:
            # self.filter_unique_lines()
        default_json ='''{
            "replace": false,
            "values": [
            ]
        }'''
        output = json.loads(default_json)
        output['values'] = [f"minecraft:{block}" for block in self.blocks]
        with open(tag_file, 'w') as f:
            try:
                print(json.dumps(output, indent=4), file=f)
            except TypeError:
                print("======Error with", self.file_name, "======")
                print(self.lines)

class SettingSign:
    TOTAL_STATES_STRING = "STATE_COUNT"
    def __init__(self, pos, template, state_id_variable, total_states) -> None:
        self.pos = pos
        self.template = template
        self.state_id_variable = state_id_variable
        self.states = []
        self.total_states = total_states
        

    def append(self, *new_state):
        self.states.append(
            execute_if_score_equals(self.state_id_variable, len(self.states),
                setblock(self.pos, AIR) +
                raw_formatted(f"setblock {tuple_to_string(self.pos)} {self.template}", *new_state) + 
                macro(f"{self.state_id_variable} %= {self.total_states}")
            )
        )
        # self.states.append(self.run_after_click)
    # def extend(self, *new_states):
        # self.states.extend(new_states)
    def build(self):
        return list_chain(self.states) + macro(f"{self.state_id_variable} %= {self.total_states}")
    

UPDATE_JSON_FILE = None
def add_update_files():
    global UPDATE_JSON_FILE
    # print(UPDATE_JSON_FILE)
    # with open(UPDATE_JSON_FILE, 'r') as f:
    #     original = f.read()
    original = '''{
    "replace": false,
    "values": []
}'''
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

reset = OutputFile("reset", force_unqiue_lines=True)
reset.append("say Reload has completed")
reset.append(f"scoreboard objectives add {CONST_SCOREBOARD_NAME} dummy")

REMAINDER_SCOREBOARD_OBJECTIVE = "remainder"
reset.append(f"scoreboard objectives add {REMAINDER_SCOREBOARD_OBJECTIVE} dummy")

helper_update = OutputFile("helper_update", is_update_file=True)

scheduled_functions = []
def call_function(function_name:OutputFile | str, delay=0, unit='t'):
    if type(function_name) is OutputFile:
        function_part = f"function {function_name.path_with_datapack_name}"
    else:
        function_part = f"function {DATAPACK_NAME}:{DATAPACK_NAME}/{function_name}"
    if delay > 0:
        scheduled_functions.append(function_part.split(" ")[1])
        return [f"schedule {function_part} {convert_to_ticks(delay, unit)} append"]
    return [function_part]

def clear_scheduled_functions():
    return [f"schedule clear {x}" for x in scheduled_functions]

run_function = call_function
get_type = type
def selector_entity(tag=None, tags=None, negative_tags=None, 
                    limit=None,type=None,dx=None,dy=None,dz=None, 
                    distance=None, sort=None, team=None,
                    score=None, scores=None, selector='@e'):
    to_go_over = list(locals().items())
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
at_p = partial(selector_entity, selector='@p')
at_s = partial(selector_entity, selector='@s')
    

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
def summon_delay_cloud(delay: int, tag: str, unit="t"):
    return ['summon area_effect_cloud ~ ~ ~ {Tags:["'f'{tag}"],Age:'+f"-{convert_to_ticks(delay, unit)}}}"]

def run_when_tag_gone(tag, to_run):
    return execute_unless(f"entity @e[type=area_effect_cloud,tag={tag}]", to_run)
allow_after_delay = run_when_tag_gone

delayed_code_id = "delayed_code_id"
delayed_code_num = 0

def delay_code_block(lines_to_delay : list, delay_time: int, unit='t'):
    global delayed_code_num
    delayed_code_num += 1
    curret_delayed_code = OutputFile(f"{delayed_code_id}{delayed_code_num}", folder="delayed_code")
    curret_delayed_code.extend(lines_to_delay)
    return call_function(curret_delayed_code, delay_time, unit)


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
    # create_scoreboard(score1, 0, owner1)
    return [f"scoreboard players operation {owner1} {score1} {op} {second_part}"]

def increment_with_bound(score1, bound : int, owner1=GLOBAL_VAR_HOLDER, owner2=GLOBAL_VAR_HOLDER):
    return operation(score1, '+=', 1, owner1, owner2) + operation(score1, '<', bound, owner1, owner2)

def decrement_with_bound(score1, bound : int, owner1=GLOBAL_VAR_HOLDER, owner2=GLOBAL_VAR_HOLDER):
    return operation(score1, '-=', 1, owner1, owner2) + operation(score1, '>', bound, owner1, owner2)

def set_to_lower(score1, bound : int, owner1=GLOBAL_VAR_HOLDER, owner2=GLOBAL_VAR_HOLDER):
    return operation(score1, '<', bound, owner1, owner2)
set_to_min = set_to_lower

def set_to_higher(score1, bound : int, owner1=GLOBAL_VAR_HOLDER, owner2=GLOBAL_VAR_HOLDER):
    return operation(score1, '>', bound, owner1, owner2)
set_to_max = set_to_higher

def decrement_with_bound(score1, bound : int, owner1=GLOBAL_VAR_HOLDER, owner2=GLOBAL_VAR_HOLDER):
    return operation(score1, '-=', 1, owner1, owner2) + operation(score1, '>', bound, owner1, owner2)

operation = scoreboard_operation
def increment(score, owner1: str = GLOBAL_VAR_HOLDER):
    return scoreboard_operation(score, '+=', 1, owner1=owner1)

def raw(text: str):
    return [line.strip().removeprefix("/") for line in text.strip().splitlines()] 

def tuple_to_relative_string(tup):
    return f"~{tup[0]} ~{tup[1]} ~{tup[2]}"

def tuple_to_string(tup):
    if type(tup) is str:
        return tup
    return " ".join(str(x) for x in tup)

def effect(target, potion_effect, time='infinite', amplifier=0, hide_particles='true'):
    return [f'effect give {target} {potion_effect} {time} {amplifier} {hide_particles}']
effect_give = effect
def effect_clear(target, effect=''):
    return [f'effect clear {target} {effect}']

def execute_at(pos : str | tuple[int, int, int], to_run : list, anchored_eyes=False):
    extra = " anchored eyes" if anchored_eyes else ""
    return [f"execute positioned {tuple_to_string(pos)}{extra} run {command}" for command in to_run]

execute_positioned = execute_at

shoot_facing_controller = OutputFile("shoot_facing_controller", force_unqiue_lines=True, is_update_file=True)
def shoot_facing(shooter=at_s(), moving_entity="marker",step=.5, max_range=60, bullet_label_tag=None, code_to_run_after_step=None, repeats_per_tick=1):
    code_to_run_after_step = [] if code_to_run_after_step is None else code_to_run_after_step
    to_move_tag = "not_adjusted"
    # move_in_facing_dir_tag = "move_in_facing_direction"
    step_size_tag = f"step_size{step}".replace(".", "_")
    current_function_name = f"{bullet_label_tag}_movement"
    temp_function = OutputFile(current_function_name, 
        (
            tp(at_s(), f"^ ^ ^{step}") + 
            code_to_run_after_step +
            execute_if_entity(f"@a[sort=nearest,limit=1,distance={max_range}..]", 
                kill(at_s())
            )
        ) * repeats_per_tick
    )
    shoot_facing_controller.extend(
        execute_as_at(at_e(tags=[step_size_tag]),
            call_function(temp_function)
        )
    )
    extra_tags = [bullet_label_tag] if bullet_label_tag is not None else []
    return summon(moving_entity, (0,0,0), tags=[to_move_tag, step_size_tag] + extra_tags) +\
        tp(at_e(tag=to_move_tag), shooter) +\
        execute_as_at(at_e(tag=to_move_tag), tp(at_s(), ABOVE)) +\
    remove_tag(at_e(tag=to_move_tag), to_move_tag)


def execute_if(condition : str, to_run : list):
    return convert_from_single_as_needed(f"execute if {condition} run", to_run)

def execute_if_entity(selector : str, to_run : list):
    return convert_from_single_as_needed(f"execute if entity {selector} run", to_run)

def execute_if_block_matches(position_to_check: str | tuple[int, int, int], block_to_match: str, to_run : list):
    if type(position_to_check) != str:
        position_to_check = tuple_to_string(position_to_check)
    return convert_from_single_as_needed(f"execute if block {position_to_check} {block_to_match} run", to_run)

execute_if_block = execute_if_block_matches

def execute_if_score(scoreboard_name : str, check: str, to_run : list, if_or_unless: str="if", owner=GLOBAL_VAR_HOLDER):
    create_scoreboard_as_needed(scoreboard_name)
    return convert_from_single_as_needed(f"execute {if_or_unless} score {owner} {scoreboard_name} {check} run", to_run)

execute_unless_score = partial(execute_if_score, if_or_unless="unless")

def execute_if_score_equals(scoreboard_name : str, value: str|int, to_run : list):
    create_scoreboard(scoreboard_name)
    return convert_from_single_as_needed(f"execute if score {GLOBAL_VAR_HOLDER} {scoreboard_name} matches {value} run", to_run)
execute_if_score_matches = execute_if_score_equals
def execute_if_score_other_score(score1 : str, op: str, score2: str, to_run : list, owner1: str=GLOBAL_VAR_HOLDER, owner2: str=GLOBAL_VAR_HOLDER, if_or_unless='if'):
    create_scoreboard_as_needed(score1)
    return convert_from_single_as_needed(f"execute {if_or_unless} score {owner1} {score1} {op} {owner2} {score2} run", to_run)

def execute_if_score_equals_score(score1 : str, score2: str, to_run : list, owner1: str=GLOBAL_VAR_HOLDER, owner2: str=GLOBAL_VAR_HOLDER):
    return execute_if_score_other_score(score1, '=', score2, to_run, owner1, owner2)
def execute_unless_score_equals_score(score1 : str, score2: str, to_run : list, owner1: str=GLOBAL_VAR_HOLDER, owner2: str=GLOBAL_VAR_HOLDER):
    return execute_if_score_other_score(score1, '=', score2, to_run, owner1, owner2, if_or_unless='unless')
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
    
def get_four_corners(pos1, pos2):
    return [pos1, (pos1[0], pos1[1], pos2[2]), (pos2[0], pos1[1], pos1[2]),  pos2]

def get_center(pos1, pos2):
    return tuple((c1 + c2) // 2 for c1, c2 in zip(pos1, pos2))

def set_score(scoreboard_name: str, value: str | int, owner: str=GLOBAL_VAR_HOLDER):
    create_scoreboard_as_needed(scoreboard_name)
    return [f"scoreboard players set {owner} {scoreboard_name} {value}"]

nested_function_number = 0
nested_functions = OutputFile("nested_function", folder="nested_functions")
nested_seen = {}
def convert_from_single_as_needed(prefix:str, to_run: str | list):
    global nested_function_number
    if type(to_run) == str:
        return [f"{prefix} {to_run}"]
    # if type(to_run[0]) == list:
    #     to_run = list_chain(to_run)
    # print(prefix)
    # before = to_run.copy()
    # print(to_run)
    to_run.sort(key=lambda x: x.startswith("tag"))
    # try:
    # except:
        # print(to_run)
        # exit()

    # if to_run != before:
        # print("NOTE: order was changed")
        # print("before:")
        # print("\n".join(before))
        # print("after:")
        # print("\n".join(to_run))
    # suffixes = [f"{command[0] if type(command) is list else command}" for command in to_run]
    inside_part = [f"{prefix} {command[0] if type(command) is list else command}" for command in to_run]
    # not_optimized = [f"{prefix} {suffix}" for suffix in suffixes]
    length_one_check = False
    length_one_check = len(inside_part) == 1
    if "nop" in sys.argv or length_one_check:
        return inside_part
    current_nest = nested_functions.add_variant(nested_function_number)
    nested_function_number += 1
    current_nest.extend(to_run)
    # calling_part = nested_functions.add_variant(nested_function_number)
    # nested_function_number += 1
    # calling_part.append(prefix + ' ' + call_function(current_nest)[0])
    ret = [[prefix][0] + ' ' + call_function(current_nest)[0]]
    return ret
    # if current_nest.content in nested_seen:
    #     nested_function_number -= 1
    #     nested_functions.pop_variant()
    #     return call_function(nested_seen[current_nest.content])

    # nested_seen[current_nest.content] = current_nest
    # ret = [[prefix][0] + ' ' + call_function(current_nest)[0]]
    # print("returning", ret)
    return call_function(current_nest)

def create_scoreboard_as_needed(scoreboard_name: str, display_name=''):
    if scoreboard_name not in scoreboard_variables_created:
        scoreboard_variables_created.add(scoreboard_name)
        reset.append(f"scoreboard objectives add {scoreboard_name} dummy {display_name}")

def set_score_to_total_of_other_scores(score_to_set, score_to_total_from_others, other_score_owner_selectors, score_to_set_owner=GLOBAL_VAR_HOLDER):
    return [
        f'scoreboard players set {score_to_set_owner} {score_to_set} 0',
        f'scoreboard players operation {score_to_set_owner} {score_to_set} += {other_score_owner_selectors} {score_to_total_from_others}']

def place(structure_to_place, pos: tuple[int, int, int] | str):
    pos = tuple_to_string(pos)
    return [f"place template {structure_to_place} {pos}"]

def execute_as(selector : str, to_run : list):
    return convert_from_single_as_needed(f"execute as {selector} run", to_run)


def execute_as_at_self(selector : str, to_run : list, anchored_eyes=False):
    extra = " anchored eyes" if anchored_eyes else ""
    return convert_from_single_as_needed(f"execute as {selector} at @s{extra} run", to_run)

execute_as_at = execute_as_at_self

def playsound(sound_name: str, pitch : float=1, to_play_sound_to_selector: str="@a at @s", volume:float=1):
    return execute_as(to_play_sound_to_selector, 
        [f"playsound {sound_name} master @s ~ ~ ~ {volume} {pitch}"]
    )

def element_wise(a, b, symbol=op.add):
    return tuple(symbol(x, y) for x, y in zip(a, b))

def place_marker(pos:str="~ ~ ~", tag=None, tags:list[str]=None):
    if tags is None:
        tags = []
    if tag is not None:
        tags.append(tag)
    return [f"summon marker {tuple_to_string(pos)}" + " {Tags:" + format_tags_for_nbt(tags) + "}"]
summon_marker = place_marker

def place_marker(pos:str="~ ~ ~", tags:list[str]=None):
    if tags is None:
        tags = []
    return [f"summon marker {tuple_to_string(pos)}" + " {Tags:" + format_tags_for_nbt(tags) + "}"]

def format_string(s, *replace_order):
    '''replaces _r1 with entries from replace_order'''
    replace_order = list(replace_order)
    return re.sub(r"_r1", lambda _: str(replace_order.pop(0)), s)

def raw_formatted(s, *replace_order):
    return [format_string(s, *replace_order)]

def summon(entity: str, position: str| tuple[int, int, int], tags:list[str]=None, no_ai=False):
    extra = '' if tags is None else (" {Tags:" + format_tags_for_nbt(tags) + ('NoAI:1b' if no_ai else '') + "}")
    return [f"summon {entity} {tuple_to_string(position)}" + extra]

def gamemode(mode, selector):
    return [f'gamemode {mode} {selector}']

def tp(from_, to_):
    if type(to_) == tuple:
        to_ = tuple_to_string(to_)
    return [f"tp {from_} {to_}"]

def fill(pos1, pos2, block, mode="replace", extra_args=''):
    '''mode can be destroy, hollow, keep, outline, or replace.
    Only replace has args after that'''
    return [f'fill {tuple_to_string(pos1)} {tuple_to_string(pos2)} {block} {mode} {extra_args}']

def setblock_filtered(pos, block, replaceable: str | list):
    # if type(replaceable) == str:
    #     replaceable = [replaceable]
    return fill(pos, pos, block, 'replace', replaceable)

def get_rectangular_prism_corners(point1, point2):
    """
    Returns the 8 corners of the rectangular prism formed by two points in 3D space.
    """
    x1, y1, z1 = point1
    x2, y2, z2 = point2

    # Determine the coordinates of the 8 corners
    corners = [(x1, y1, z1), (x1, y1, z2), (x1, y2, z1), (x1, y2, z2),
               (x2, y1, z1), (x2, y1, z2), (x2, y2, z1), (x2, y2, z2)]

    return corners

def border(point1, point2, block):
    """
    Draws the outline of the rectangular prism formed by two points in 3D space
    using the draw_line() function.
    """
    corners = get_rectangular_prism_corners(point1, point2)

    # Draw the edges of the rectangular prism
    return list(it.chain(fill(corners[0], corners[1], block),
    fill(corners[0], corners[2], block),
    fill(corners[0], corners[4], block),
    fill(corners[1], corners[3], block),
    fill(corners[1], corners[5], block),
    fill(corners[2], corners[3], block),
    fill(corners[2], corners[6], block),
    fill(corners[3], corners[7], block),
    fill(corners[4], corners[5], block),
    fill(corners[4], corners[6], block),
    fill(corners[5], corners[7], block),
    fill(corners[6], corners[7], block)))


def setblock(pos1, block, mode="replace"):
    '''mode can be destroy, keep, or replace.'''
    return [f'setblock {tuple_to_string(pos1)} {block} {mode}']

def clone(pos1, pos2, place_at_pos, mode="replace"):
    '''mode can be destroy, keep, or replace.'''
    return [f'clone {tuple_to_string(pos1)} {tuple_to_string(pos2)} {tuple_to_string(place_at_pos)} {mode}']


def say(*to_say:str):
    return [f"say {' '.join(str(x) for x in to_say)}"]

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



def output_commands(file, commands):
    print("\n".join(commands), file=file)

def write_scoreboard_line(mc_function_line):
    reset.append(mc_function_line)

def write_scoreboard_lines(mc_function_lines):
    reset.extend(mc_function_lines)

def increment_each_tick(scoreboard_name, selector=GLOBAL_VAR_HOLDER):
    helper_update.append(f"scoreboard players add {selector} {scoreboard_name} 1")

def increment_with_bound():
    operation()

def list_chain(x):
    return list(it.chain.from_iterable(x))

def add_scoreboard(scoreboard_name, display_name='', criteria='dummy'):
    display_name = f'"{display_name}"'
    return [f'scoreboard objectives add {scoreboard_name} {criteria} {display_name}']

def remove_scoreboard(scoreboard_name):
    return [f"scoreboard objectives remove {scoreboard_name}"]

def create_scoreboard(scoreboard_name: str, val=None, holder=GLOBAL_VAR_HOLDER, display_name=''):
    create_scoreboard_as_needed(scoreboard_name, display_name)
    if val is not None:
        # print("ran here")
        reset.append(f"scoreboard players set {holder} {scoreboard_name} {val}")
    return scoreboard_name
    # write_scoreboard_line(scoreboard_set_value_template.format(holder, scoreboard_name, 0 if val is None else val ))

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

# end_of_tick_code = OutputFile("end_of_tick_code", is_update_file=True)