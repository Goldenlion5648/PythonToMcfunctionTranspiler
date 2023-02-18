import os
from datetime import datetime 
import shutil
import pathlib

file_to_copy = "template.py"
# with open(file_to_copy) as f:
#     template = f.read()

dir_to_check ="../saves"
worlds = os.listdir(dir_to_check)
worlds = [((full_path:=f"{dir_to_check}/{world}"), 
            datetime.fromtimestamp(os.path.getmtime(full_path)))
             for world in worlds]
worlds.sort(key= lambda x : x[1])
# for world in worlds:
    # print(world)
chosen_dir = worlds[-1][0]
current_pack_name = os.listdir(f"{chosen_dir}/datapacks")[0]

path = os.path.abspath(chosen_dir)
print(path)
shutil.copyfile(file_to_copy, os.path.abspath(f"{chosen_dir}/datapacks/{current_pack_name}/data/{current_pack_name}/functions/{current_pack_name}/gen_files_for_{current_pack_name}.py"))