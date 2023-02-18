setblock ~ ~ ~ 
execute unless block ~ ~ ~-1 stone_bricks run clone ~-1 ~ ~-1
execute as @a run execute store result score @p rot run data get entity @p Rotation

data get entity @p Pos[0]

execute if score @s x_pos matches 100..130
execute store result score @a alive_time run data get entity @s Pos
execute unless  score @s x_pos = @s old_x_pos run 