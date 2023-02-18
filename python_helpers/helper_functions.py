import re
import os
import atexit
import json

update_files = []
folders_in_path = os.getcwd().split(os.sep)
DATAPACK_NAME = folders_in_path[folders_in_path.index("datapacks") + 1]
class OutputFile:
    def __init__(self, file_no_ext, data=None, is_update_file=False) -> None:
        self.file_name = f"{file_no_ext}"
        self.file_name_with_ext = f"{file_no_ext}.mcfunction"
        self.lines = [] if data is None else data
        if is_update_file:
            update_files.append(file_no_ext)
            atexit.register(add_update_files)

        atexit.register(self.write_to_file)
    def append(self, line):
        self.lines.append(line)
        
    def extend(self, line):
        self.lines.extend(line)
    
    def write_to_file(self):
        # print(self.lines)
        with open(self.file_name_with_ext, 'w') as f:
            try:
                print("\n".join(self.lines), file=f)
            except TypeError:
                print("======Error with", self.file_name, "======")
                print(self.lines)

has_made_scoreboard_file = False
scoreboard_creation_template = "scoreboard objectives add {} dummy"
scoreboard_set_value_template = "scoreboard players set {} {} {}"
VAR_HOLDER = 'global'
scoreboard_variables_created = set()

reset = OutputFile("reset")
reset.append("say Reload has completed")
helper_update = OutputFile("helper_update")

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

def call_function(function_name:OutputFile):
    return f"function {DATAPACK_NAME}:{DATAPACK_NAME}/{function_name.file_name}"

def checkerboard_pattern(block1 : str, block2 : str, lower_x, lower_y, upper_x, upper_y):
    _, block1_name = block1.split(":")
    _, block2_name = block2.split(":")
    cur_checkerboard = OutputFile(f"checkerboard_{block1_name}_{block2_name}")
    for y in range(lower_y, upper_y + 1):
        for x in range(lower_x, upper_x + 1):
            to_place = block1 if (x + y) % 2 == 0 else block2
            cur_checkerboard.append(f"setblock {x} ~ {y} {to_place}")
    cur_checkerboard.write_to_file()

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
    return [f"execute if {condition} run {command}" for command in to_run]

def execute_if_score(scoreboard_name : str, check: str, to_run : list):
    create_scoreboard_as_needed(scoreboard_name)
    return convert_from_single_as_needed(f"execute if score {VAR_HOLDER} {scoreboard_name} {check} run", to_run)

def execute_unless(condition : str, to_run : list):
    return convert_from_single_as_needed(f"execute unless {condition} run", to_run)

def store_scores(selector: str, scoreboard_and_nbt: list[tuple[str, str]]):
    return [f"execute store result score {selector} {scoreboard_name} run data get entity @s {nbt_path}" for scoreboard_name, nbt_path in scoreboard_and_nbt]

def store_count_entity_score(scoreboard_name: str, entity_selector: str, score_owner=VAR_HOLDER):
    return [f"execute store result score {score_owner} {scoreboard_name} run execute if entity {entity_selector}"]

def set_score_from(scoreboard_name: str, get_score_from: str, owner: str=VAR_HOLDER):
    create_scoreboard_as_needed(scoreboard_name)
    return f"execute store result score {owner} {scoreboard_name} {get_score_from}"

def set_score(scoreboard_name: str, value: str | int, owner: str=VAR_HOLDER):
    create_scoreboard_as_needed(scoreboard_name)
    return [f"scoreboard players set {owner} {scoreboard_name} {value}"]

def convert_from_single_as_needed(prefix:str, to_run: str | list):
    if type(to_run) == str:
        return [f"{prefix} {to_run}"]
    return [f"{prefix} {command}" for command in to_run]

def create_scoreboard_as_needed(scoreboard_name: str):
    if scoreboard_name not in scoreboard_variables_created:
        create_scoreboard(scoreboard_name, 0)

def execute_as(selector : str, to_run : list):
    return convert_from_single_as_needed(f"execute as {selector} run", to_run)

def element_wise(a, b):
    return tuple(x + y for x, y in zip(a, b))

def output_commands(file, commands):
    print("\n".join(commands), file=file)

def write_scoreboard_line(mc_function_line):
    reset.append(mc_function_line)

def increment_each_tick(scoreboard_name, selector=VAR_HOLDER):
    helper_update.append(f"scoreboard players add {selector} {scoreboard_name} 1")

def create_scoreboard(scoreboard_name: str, val=None, holder=VAR_HOLDER):
    if scoreboard_name not in scoreboard_variables_created:
        scoreboard_variables_created.add(scoreboard_name)
        reset.append(f"scoreboard objectives add {scoreboard_name} dummy")
    if val is not None:
        write_scoreboard_line(scoreboard_set_value_template.format(holder, scoreboard_name, val))


def eval_macro(line : str):
    var, op, value = re.search(r"([a-z\d_]+)([^a-z\d]+)(\d+)", line).groups()
    var = var.strip()
    op = op.strip()
    value = value.strip()
    # print(var, op, value)
    const_holder = f"const{value}"
    if op == "=":
        # create_scoreboard(var, value)
        # create_scoreboard_as_needed(var)
        # to_write = f"scoreboard players set {VAR_HOLDER} {var} {value}"
        return set_score(var, value)
    const_score_name = "num_value"
    create_scoreboard(const_score_name, value, const_holder)
    return [f"scoreboard players operation {VAR_HOLDER} {var} {op} {const_holder} {const_score_name}"]
        # write_scoreboard_line(to_write)
macro = eval_macro