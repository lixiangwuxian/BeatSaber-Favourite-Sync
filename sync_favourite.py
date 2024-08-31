import json
import os
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

def adb_pull_player_data(device_id):
    """使用 ADB 从连接的设备拉取 PlayerData.dat 文件"""
    local_temp_path = "PlayerData_vr.dat"
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
        shutil.copy("PlayerData_vr.dat", mtp_path)
        print(f"成功将修改后的 PlayerData.dat 写回到 MTP 设备路径 {mtp_path}")
    except Exception as e:
        print(f"写回 MTP 设备文件时出错: {e}")

def sync_favorites(local_data, vr_data):
    """同步 favoritesLevelIds 项"""
    local_favorites = set(local_data['localPlayers'][0]['favoritesLevelIds'])
    vr_favorites = set(vr_data['localPlayers'][0]['favoritesLevelIds'])

    # 合并两个集合
    combined_favorites = list(local_favorites.union(vr_favorites))

    # 更新两个数据
    local_data['localPlayers'][0]['favoritesLevelIds'] = combined_favorites
    vr_data['localPlayers'][0]['favoritesLevelIds'] = combined_favorites

def main():
    user_home = os.path.expanduser('~')
    local_path = os.path.join(user_home, 'AppData', 'LocalLow', 'Hyperbolic Magnetism', 'Beat Saber', 'PlayerData.dat')

    if not os.path.exists(local_path):
        print(f"本地文件 {local_path} 不存在！")
        return

    print("同步 VR 设备和本地的 PlayerData.dat 文件中的 favoritesLevelIds 项")
    devices = detect_adb_devices()

    device_type = None
    device_id = None
    vr_path = None

    if devices:
        print("检测到 ADB 设备。")
        device_id = devices[0]  # 假设仅有一个设备
        vr_path = adb_pull_player_data(device_id)
        device_type = 'adb'
        if not vr_path:
            return
    else:
        print("未检测到 ADB 设备，尝试检测 MTP 设备...")
        potential_paths = find_mtp_device_path()
        if potential_paths:
            print("检测到 MTP 设备上的 PlayerData.dat 文件路径。")
            vr_path = potential_paths[0]  # 假设仅有一个设备
            device_type = 'mtp'
        else:
            print("未检测到任何 MTP 设备上的 PlayerData.dat 文件。")
            return

    local_data = load_player_data(local_path)
    vr_data = load_player_data(vr_path)

    # 同步 favoritesLevelIds
    sync_favorites(local_data, vr_data)

    # 保存同步后的数据
    save_player_data(local_path, local_data)
    save_player_data("PlayerData_vr.dat", vr_data)

    # 将修改后的文件写回设备
    if device_type == 'adb' and device_id:
        adb_push_player_data(device_id, "PlayerData_vr.dat")
    elif device_type == 'mtp' and vr_path:
        mtp_copy_player_data_back(vr_path)

    print("同步完成，已更新本地和设备上的 PlayerData.dat 文件。")

if __name__ == '__main__':
    main()
