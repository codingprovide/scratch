import os
import json
import zipfile


def extract_project_json(sb3_file, extract_to):
    with zipfile.ZipFile(sb3_file, "r") as zip_ref:
        zip_ref.extract("project.json", extract_to)
        # 解壓縮其他文件（除了 project.json）
        for file in zip_ref.namelist():
            if file != "project.json":
                zip_ref.extract(file, extract_to)


def merge_json_files(input_folder, output_file):
    if not os.path.exists(input_folder):
        print(f"指定的資料夾路徑 '{input_folder}' 不存在。請檢查路徑是否正確。")
        exit(1)

    merged_data = None
    temp_folder = "./temp_json"

    if not os.path.exists(temp_folder):
        os.makedirs(temp_folder)

    # 遍歷資料夾內所有文件
    for filename in os.listdir(input_folder):
        if filename.endswith(".sb3"):
            sb3_file_path = os.path.join(input_folder, filename)
            try:
                extract_project_json(sb3_file_path, temp_folder)
                json_file_path = os.path.join(temp_folder, "project.json")
                with open(json_file_path, "r", encoding="utf-8") as json_file:
                    data = json.load(json_file)
            except (json.JSONDecodeError, UnicodeDecodeError, zipfile.BadZipFile) as e:
                print(f"文件 {filename} 不是有效的 sb3 文件或無法解壓，跳過。錯誤：{e}")
                continue

            # 確保 JSON 文件符合 Scratch 的 sb3 格式
            if "targets" not in data:
                print(f"文件 {filename} 缺少 'targets' 部分，無法合併。")
                continue

            # 初始化 merged_data 為第一個項目，或者合併角色/背景
            if merged_data is None:
                merged_data = data
            else:
                # 合併角色（targets）
                for target in data["targets"]:
                    if not target["isStage"]:
                        # 查找是否已有重複角色名稱，如果有則覆蓋
                        existing_target = next(
                            (
                                t
                                for t in merged_data["targets"]
                                if t["name"] == target["name"] and not t["isStage"]
                            ),
                            None,
                        )
                        if existing_target:
                            merged_data["targets"].remove(existing_target)
                        merged_data["targets"].append(target)
                        break

    # 將合併後的數據寫入新的 JSON 文件
    if merged_data is not None:
        with open(output_file, "w", encoding="utf-8") as output_json_file:
            json.dump(merged_data, output_json_file, indent=4, ensure_ascii=False)

    # 壓縮成新的 sb3 文件
    with zipfile.ZipFile("all_merage.sb3", "w") as new_sb3:
        # 添加合併後的 project.json
        new_sb3.write(output_file, "project.json")
        # 添加其他資源文件
        for root, _, files in os.walk(temp_folder):
            for file in files:
                if file != "project.json":
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_folder)
                    new_sb3.write(file_path, arcname)

    # 清理暫存資料夾
    if os.path.exists(temp_folder):
        for temp_file in os.listdir(temp_folder):
            os.remove(os.path.join(temp_folder, temp_file))
        os.rmdir(temp_folder)


if __name__ == "__main__":
    input_folder = os.getcwd()  # 使用當前所在位置的資料夾
    output_file = "project.json"  # 合併後輸出的 JSON 文件名
    merge_json_files(input_folder, output_file)
    print(f"所有 sb3 文件已合併至 all_merage.sb3")

# 注意事項：
# 1. JSON 文件格式：程式會檢查每個解壓出的 JSON 文件是否包含 'targets' 部分，以確保符合 Scratch 的 sb3 JSON 格式。
# 2. 重複角色：如果角色名稱重複，則會覆蓋之前的角色，保留最新的角色。
# 3. 報錯處理：如果某些 sb3 文件無法解壓或解析錯誤，程式會輸出錯誤訊息，但不會中斷整個合併過程。
