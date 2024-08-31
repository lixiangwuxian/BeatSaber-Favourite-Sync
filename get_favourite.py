import json
import os
import glob
import subprocess

def load_player_data(file_path):
    """加载 PlayerData.dat 文件内容"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data

def save_player_data(file_path, data):
    """保存修改后的 PlayerData.dat 文件内容"""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def export_favorites(data, export_path):
    """导出 favoritesLevelIds 为 JSON 数组文件"""
    favorites = data['localPlayers'][0]['favoritesLevelIds']
    with open(export_path, 'w', encoding='utf-8') as f:
        json.dump(favorites, f, ensure_ascii=False, indent=4)
    print(f"成功导出到 {export_path}")

def import_favorites(data, import_path):
    """导入 JSON 数组文件并去重后添加到 favoritesLevelIds"""
    with open(import_path, 'r', encoding='utf-8') as f:
        new_favorites = json.load(f)

    current_favorites = data['localPlayers'][0]['favoritesLevelIds']
    combined_favorites = list(set(current_favorites + new_favorites))

    data['localPlayers'][0]['favoritesLevelIds'] = combined_favorites
    print(f"成功导入并合并了 {import_path} 中的关卡ID")

def list_json_files():
    """列出当前目录下的所有 JSON 文件"""
    json_files = glob.glob('*.json')
    return json_files

def adb_pull_player_data(device_id):
    """使用 ADB 从连接的设备拉取 PlayerData.dat 文件"""
    local_temp_path = "PlayerData.dat"
    device_path = "/sdcard/Android/data/com.beatgames.beatsaber/files/PlayerData.dat"
    
    try:
        subprocess.run(["adb", "-s", device_id, "pull", device_path, local_temp_path], check=True)
        print(f"成功从设备 {device_id} 拉取 {device_path} 到本地 {local_temp_path}")
        return local_temp_path
    except subprocess.CalledProcessError:
        print("ADB 拉取文件失败，请检查设备连接和文件路径。")
        return None

def adb_push_player_data(device_id, local_path):
    """使用 ADB 将修改后的 PlayerData.dat 写回到设备"""
    device_path = "/sdcard/Android/data/com.beatgames.beatsaber/files/PlayerData.dat"
    
    try:
        subprocess.run(["adb", "-s", device_id, "push", local_path, device_path], check=True)
        print(f"成功将 {local_path} 写回到设备 {device_id} 的 {device_path}")
    except subprocess.CalledProcessError:
        print("ADB 写入文件失败，请检查设备连接和文件路径。")

def detect_adb_devices():
    """检测通过 ADB 连接的设备"""
    try:
        result = subprocess.run(["adb", "devices"], capture_output=True, text=True)
        devices = [line.split()[0] for line in result.stdout.splitlines() if line.endswith("device")]
        return devices
    except FileNotFoundError:
        print("未检测到 ADB，请确保 ADB 已正确安装并添加到系统 PATH 中。")
        return []

def find_mtp_device_path():
    """查找已连接的 MTP 设备路径并返回可能的 PlayerData.dat 文件路径"""
    base_mtp_path = r'\\'  # MTP 设备的基础路径
    potential_devices = []

    # 尝试获取所有连接的 MTP 设备
    try:
        for root, dirs, files in os.walk(base_mtp_path):
            for directory in dirs:
                if '内部共享存储空间' in directory or 'Internal shared storage' in directory:
                    potential_path = os.path.join(root, directory, 'Android', 'data', 'com.beatgames.beatsaber', 'files', 'PlayerData.dat')
                    if os.path.exists(potential_path):
                        potential_devices.append(potential_path)
            break  # 仅扫描一次根目录以找到设备
    except Exception as e:
        print(f"扫描 MTP 设备时出错: {e}")

    return potential_devices

def mtp_copy_player_data_back(mtp_path):
    """将修改后的 PlayerData.dat 写回到 MTP 设备"""
    try:
        shutil.copy("PlayerData.dat", mtp_path)
        print(f"成功将修改后的 PlayerData.dat 写回到 MTP 设备路径 {mtp_path}")
    except Exception as e:
        print(f"写回 MTP 设备文件时出错: {e}")

def select_device(devices):
    """让用户选择设备"""
    print("检测到以下设备：")
    for idx, device in enumerate(devices):
        print(f"{idx + 1}. {device}")
    choice = input("请选择设备编号: ").strip()
    if choice.isdigit() and 1 <= int(choice) <= len(devices):
        return devices[int(choice) - 1]
    else:
        print("无效的选项！")
        return None

def main():
    user_home = os.path.expanduser('~')
    default_path = os.path.join(user_home, 'AppData', 'LocalLow', 'Hyperbolic Magnetism', 'Beat Saber', 'PlayerData.dat')

    print(f"默认 PlayerData.dat 路径为: {default_path}")
    player_data_path = input("请输入 PlayerData.dat 文件的路径（或按回车使用默认路径，输入 'android' 从 VR 设备读取）: ").strip()

    device_type = None
    device_id = None

    if player_data_path.lower() == 'android':
        devices = detect_adb_devices()
        if devices:
            print("检测到 ADB 设备。")
            device_id = select_device(devices)
            if device_id:
                player_data_path = adb_pull_player_data(device_id)
                device_type = 'adb'
                if not player_data_path:
                    return
            else:
                return
        else:
            print("未检测到 ADB 设备，尝试检测 MTP 设备...")
            potential_paths = find_mtp_device_path()
            if potential_paths:
                print("检测到 MTP 设备上的 PlayerData.dat 文件路径。")
                device_path = select_device(potential_paths)
                if device_path:
                    player_data_path = device_path
                    device_type = 'mtp'
                else:
                    return
            else:
                print("未检测到任何 MTP 设备上的 PlayerData.dat 文件。")
                return
    elif not player_data_path:
        player_data_path = default_path
    else:
        # 去除路径字符串两端可能存在的双引号
        player_data_path = player_data_path.strip('"')

    if not os.path.exists(player_data_path):
        print(f"文件 {player_data_path} 不存在！")
        return

    data = load_player_data(player_data_path)

    print("请选择操作：")
    print("1. 导出 favoritesLevelIds 到 JSON 文件")
    print("2. 从 JSON 文件导入 favoritesLevelIds")
    choice = input("请输入选项 (1 或 2): ").strip()

    if choice == '1':
        # 导出 favoritesLevelIds 到文件
        export_path = 'exported_favorites.json'
        export_favorites(data, export_path)
    elif choice == '2':
        # 自动搜索当前目录下的 JSON 文件并提供选择
        json_files = list_json_files()
        if not json_files:
            print("当前目录下没有找到 JSON 文件！")
            return
        
        print("找到以下 JSON 文件：")
        for idx, file in enumerate(json_files):
            print(f"{idx + 1}. {file}")
        
        file_choice = input("请选择要导入的文件编号: ").strip()
        if file_choice.isdigit() and 1 <= int(file_choice) <= len(json_files):
            import_path = json_files[int(file_choice) - 1]
            import_favorites(data, import_path)
            save_player_data("PlayerData.dat", data)

            # 将修改后的文件写回设备
            if device_type == 'adb' and device_id:
                adb_push_player_data(device_id, "PlayerData.dat")
            elif device_type == 'mtp' and player_data_path:
                mtp_copy_player_data_back(player_data_path)
        else:
            print("无效的选项！请重新运行脚本并输入有效的选项。")
    else:
        print("无效的选项！请重新运行脚本并输入有效的选项。")

if __name__ == '__main__':
    main()
