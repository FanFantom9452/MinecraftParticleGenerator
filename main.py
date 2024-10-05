import math
import pyperclip
import os
import random

# 計算單個機械手臂旋轉後的位置
def calculate_position(arm_length, angle_deg):
    angle_rad = math.radians(angle_deg)  # 將角度轉為弧度
    x = arm_length * math.cos(angle_rad)  # 左右
    z = arm_length * math.sin(angle_rad)  # 前後
    return x, z

# 計算最終位置並生成粒子指令 (相對於玩家視角 ^ ^ ^ 格式)
def generate_particle_commands(prefix_input="flame", suffix_input="0 0 0 0.1 0 force @a[distance=..50]",
                               arm_data=None, iterations=None, offset=None, initial_offset=None, 
                               auto_tag=False, radius=1, start_angle=0):
    x_offset, y_offset, z_offset = offset  # 每次旋轉的偏差
    initial_x_offset, initial_y_offset, initial_z_offset = initial_offset  # 初始偏差
    particle_commands = []
    
    for i in range(iterations):
        total_x = 0  # 對應於 ^ (左右)
        total_y = 0  # 對應於 ^ (上下)
        total_z = 0  # 對應於 ^ (前後)
        
        # 計算每個機械手臂對應的位移
        for arm_length, angle_step in arm_data:
            angle = (start_angle + angle_step * i) % 360  # 加入起始角度進行旋轉
            x, z = calculate_position(arm_length, angle)
            total_x += x  # 左右方向
            total_z += z  # 前後方向
        
        total_y += i * y_offset  # 每次迴圈, Y軸的變化 (上下)

        # 計算最終偏移位置
        final_x = round(initial_x_offset + total_x + i * x_offset, 2)
        final_y = round(initial_y_offset + total_y, 2)
        final_z = round(initial_z_offset + total_z + i * z_offset, 2)
        
        # 使用相對座標 ^ ^ ^ 生成粒子效果指令
        particle_command = f"particle {prefix_input} ^{final_x} ^{final_y} ^{final_z} {suffix_input}"
        particle_commands.append(particle_command)
        
        # 如果選擇自動標記敵人, 生成標記指令
        if auto_tag:
            tag_command = (f"execute positioned ^{final_x} ^{final_y} ^{final_z} run "
                           f"tag @e[type=!#system:nothing,tag=!target,distance=..{radius}] add target")
            particle_commands.append(tag_command)
    
    return particle_commands

def read_numbers_from_txt(file_path):
    """從文件中讀取已經存在的 UUID 字串, 並將其存入集合以避免重複"""
    # Create Empty File
    if not os.path.exists(file_path):
        with open(file_path, 'w') as file:
            pass  
    
    uuids = set()  # 使用集合避免重複
    with open(file_path, 'r') as file:
        for line in file:
            if line.strip():
                uuids.add(line.strip())
    return uuids

def write_number_to_txt(file_path, uuids):
    """將生成的新 UUID 字串寫入文件, 每行一個"""
    with open(file_path, 'a') as file:
        for uuid in uuids:
            file.write(f"{uuid}\n")

def generate_random_signed_32bit_integer():
    """生成一個隨機的有號32位元整數"""
    return random.randint(-2147483648, 2147483647)

def format_uuid_from_integers(int_list):
    """將4個有號32位元整數轉換為UUID格式的字串"""
    # 轉換每個整數為16進制, 並用0填充至8位長度
    hex_parts = [f'{i & 0xFFFFFFFF:08x}' for i in int_list]
    
    # 組合成UUID格式的字串
    return f"{hex_parts[0]}-{hex_parts[1][:4]}-{hex_parts[1][4:]}-{hex_parts[2][:4]}-{hex_parts[2][4:]}{hex_parts[3]}"

def generate_random_uuid(already_used):
    """生成不與已存在的UUID重複的隨機UUID"""
    while True:
        # 生成4個隨機的有號32位元整數
        random_integers = [generate_random_signed_32bit_integer() for _ in range(4)]
        
        # 生成符合UUID格式的字串
        uuid_str = format_uuid_from_integers(random_integers)
        
        # 檢查是否與已存在的UUID重複
        if uuid_str not in already_used:
            # 將該組整數轉為目標格式: {UUID:[I; <整數1>, <整數2>, <整數3>, <整數4>]}
            uuid_obj = f"UUID:[I; {random_integers[0]}, {random_integers[1]}, {random_integers[2]}, {random_integers[3]}]"
            return uuid_str, uuid_obj

def generate_marker_to_particle_commands(prefix_input="flame", suffix_input="0 0 0 0.1 0 force @a[distance=..50]",
                               arm_data=None, iterations=None, offset=None, initial_offset=None, 
                               auto_tag=False, radius=1, start_angle=0):
    x_offset, y_offset, z_offset = offset  # 每次旋轉的偏差
    initial_x_offset, initial_y_offset, initial_z_offset = initial_offset  # 初始偏差
    particle_commands = []

    # 歷史使用過的UUID
    file_path = "history.txt"
    
    # 讀取已經存在的UUID字串集合
    already_used_uuids = read_numbers_from_txt(file_path)
    new_uuids_str = []
    new_uuids_obj = []

    # 生成與已用UUID不重複的隨機UUID
    for _ in range(len(arm_data)):
        new_uuid_str, new_uuid_obj = generate_random_uuid(already_used_uuids)
        new_uuids_obj.append(new_uuid_obj)
        new_uuids_str.append(new_uuid_str)
        already_used_uuids.add(new_uuid_str)  # 添加新的UUID字串到已使用的集合
    
    # 將新生成的UUID寫入文件
    write_number_to_txt(file_path, new_uuids_obj)

    #初始設定
    particle_commands.append("# Initialization / 初始化設定")
    particle_commands.append("forceload add -1 -1 0 0")
    particle_commands.append('scoreboard objectives add particle_worker dummy "Particle Worker"')
    count = 0
    for arm_length, angle_step in arm_data:
        rotate_command = 'execute unless entity '+ new_uuids_str[count] +' run summon marker 0 0 0 {Tags:["particle_gen"],Rotation:['+ str(start_angle) +'f,0f],'+ new_uuids_obj[count] +'}'
        particle_commands.append(rotate_command)
        count += 1


    #處理原地旋轉部分
    count = 0
    particle_commands.append("# Rotate By Self / 原地旋轉")
    for arm_length, angle_step in arm_data:
        rotate_command = f"execute as {new_uuids_str[count]} at @s run tp @s ~ ~ ~ ~{angle_step} ~"
        particle_commands.append(rotate_command)
        count += 1

    #產生粒子特效部分
    count = 0
    particle_commands.append("# Particle / 生成粒子效果")
    gen_particle_command = f"execute positioned ~{initial_x_offset} ~{initial_y_offset} ~{initial_z_offset} "
    tag_command = f"execute positioned ~{initial_x_offset} ~{initial_y_offset} ~{initial_z_offset} "
    for arm_length, angle_step in arm_data:
        gen_particle_command += f"rotated as {new_uuids_str[count]} positioned ^ ^ ^{arm_length} "
        tag_command += f"rotated as {new_uuids_str[count]} positioned ^ ^ ^{arm_length} "
        count += 1
    gen_particle_command += f"run particle {prefix_input} ~ ~0.1 ~ {suffix_input}"
    tag_command += f"run tag @e[type=!#system:nothing,tag=!target,distance=..{radius}] add target"
    particle_commands.append(gen_particle_command)
    # 如果選擇自動標記敵人, 生成標記指令
    if auto_tag:
        particle_commands.append(tag_command)
    #記分板 & 停止條件
    particle_commands.append("# Recursion / 遞迴停止條件")
    particle_commands.append("scoreboard players add t particle_worker 1")
    particle_commands.append(f"execute if score t particle_worker matches ..{iterations} positioned ~{x_offset} ~{y_offset} ~{z_offset} run function foo:bar")
    particle_commands.append(f"execute if score t particle_worker matches {iterations+1} run scoreboard players set t particle_worker 0")

    return particle_commands

def main():
    # 記錄輸入參數的列表
    input_summary = ["#=================================================================================",
                     "#This file was generated by a particle effect generator created by Fan_Fan_tom.",
                     "#You can learn how to use it through the link below:",
                     "#這個檔案是由 FanFantom 製作的粒子效果生成器產生的",
                     "#你可以點底下的連結學習如何使用",
                     "#https://github.com/FanFantom9452/MinecraftParticleGenerator",
                     "#================================================================================="]
    
    #是否使用marker來繪製特效
    is_use_marker_to_calculate = input("Use marker to calculate the position of particle effect? | 使用marker計算特效位置?\n(Input 1 or 0) | (輸入 1 或 0) : " or 0)
    if is_use_marker_to_calculate == "1":
        is_use_marker_to_calculate = True
    else:
        is_use_marker_to_calculate = False
    input_summary.append(f"#Use marker to calculate the position of particle effect? | 使用marker計算特效位置? : {'Yes' if is_use_marker_to_calculate else 'No'}")

    #要使用什麼粒子效果
    prefix_input = input("Particle Name | 粒子效果名稱\n(default is flame, press Enter to use the default) | (預設是 flame, 按 Enter 使用預設) : ")
    suffix_input = input("Particle effect parameters | 粒子特效參數\n(Default is 0 0 0 0.1 0 force @a[distance=..50], press Enter to use the default) | (預設是 0 0 0 0.1 0 force @a[distance=..50], 按 Enter 使用預設) : ")

    # 如果使用者直接按 Enter, 使用預設值
    if not prefix_input.strip():  # 檢查是否為空
        prefix_input = "flame"
    if not suffix_input.strip():  # 檢查是否為空
        suffix_input = "0 0 0 0.1 0 force @a[distance=..50]"

    # 將結果丟到 input_summary
    input_summary.append(f"#Particle Name | 粒子效果名稱 : {prefix_input}")
    input_summary.append(f"#Particle effect parameters | 粒子特效參數 : {suffix_input}")

    # 是否自動標記敵人
    auto_tag = input("Automatically tag entities that the effect passes through? | 是否自動幫特效經過的實體加上tag?\n(Input 1 or 0) | (輸入 1 或 0) : " or 0).strip() == "1"
    input_summary.append(f"#Automatically tag entities that the effect passes through? | 是否自動幫特效經過的實體加上tag? : {'Yes' if auto_tag else 'No'}")

    radius = 1  # 預設半徑
    if auto_tag:
        radius = float(input("Detection radius for tagging each particle effect | 每個粒子效果加上tag的偵測半徑\n(Default 1) | (預設 1) : ") or 1)  # 預設半徑1
        input_summary.append(f"#Detection radius for tagging each particle effect | 每個粒子效果加上tag的偵測半徑 : {radius}")

    # 問用戶起始角度, 預設為0度
    start_angle = float(input("Starting angle | 起始角度\n(0~359, default is 0) | (0~359, 預設為 0) : ") or 0)
    input_summary.append(f"#Starting angle | 起始角度: {start_angle}")

    # 取得初始中心偏差
    initial_x_offset = float(input("Initial X offset | 初始 X 偏差 (Default 0) : ") or 0)
    initial_y_offset = float(input("Initial Y offset | 初始 Y 偏差 (Default 0) : ") or 0)
    initial_z_offset = float(input("Initial Z offset | 初始 Z 偏差 (Default 0) : ") or 0)

    input_summary.append(f"#Initial X offset | 初始 X 偏差 : {initial_x_offset}")
    input_summary.append(f"#Initial Y offset | 初始 Y 偏差 : {initial_y_offset}")
    input_summary.append(f"#Initial Z offset | 初始 Z 偏差 : {initial_z_offset}")

    num_arms = int(input("Robotic arm count | 機械手臂的數量 (Default 1) : ") or 1)
    input_summary.append(f"#Robotic arm count | 機械手臂的數量 : {num_arms}")
    arm_data = []

    for i in range(num_arms):
        length = float(input(f"Arm {i+1} Length | 第 {i+1} 個機械手臂的長度 (Default 1) : ") or 1)
        angle_step = float(input(f"Arm {i+1} Rotation Angle | 第 {i+1} 個機械手臂的旋轉度數 (Default 1) : ") or 1)
        arm_data.append((length, angle_step))
        input_summary.append(f"#Arm {i+1} Length | 第 {i+1} 個機械手臂的長度 : {length}")
        input_summary.append(f"#Arm {i+1} Rotation Angle | 第 {i+1} 個機械手臂的旋轉度數 : {angle_step}")

    iterations = int(input("All arms rotation count | 所有機械手臂要旋轉幾次 (Default 50) : ") or 50)
    input_summary.append(f"#All arms rotation count | 所有機械手臂要旋轉幾次: {iterations}")
    offset_x = float(input("X offset per rotation | 每次旋轉的 X 偏差 (Default 0) : ") or 0)
    offset_y = float(input("Y offset per rotation | 每次旋轉的 Y 偏差 (Default 0) : ") or 0)
    offset_z = float(input("Z offset per rotation | 每次旋轉的 Z 偏差 (Default 0) : ") or 0)

    # 添加每次旋轉偏差到 input_summary
    input_summary.append(f"#X offset per rotation | 每次旋轉的 X 偏差 : {offset_x}")
    input_summary.append(f"#Y offset per rotation | 每次旋轉的 Y 偏差 : {offset_y}")
    input_summary.append(f"#Z offset per rotation | 每次旋轉的 Z 偏差 : {offset_z}")


    # 生成指令
    particle_commands = []
    if (is_use_marker_to_calculate):
        particle_commands = generate_marker_to_particle_commands(prefix_input, suffix_input, arm_data, iterations, 
                                                                 (offset_x, offset_y, offset_z), 
                                                                 (initial_x_offset, initial_y_offset, initial_z_offset), 
                                                                 auto_tag, radius, start_angle)
    else:
        particle_commands = generate_particle_commands(prefix_input, suffix_input, arm_data, iterations, 
                                                        (offset_x, offset_y, offset_z), 
                                                        (initial_x_offset, initial_y_offset, initial_z_offset), 
                                                        auto_tag, radius, start_angle)
    
    # 輸入參數加到結果的最上方
    commands_str = "\n".join(input_summary) + "\n" + "\n".join(particle_commands)
    
    # 複製到剪貼簿
    pyperclip.copy(commands_str)
    print("Copied to clipboard | 已複製到剪貼簿")

if __name__ == "__main__":
    main()