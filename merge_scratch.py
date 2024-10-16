import os
import json
import zipfile
import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox


def extract_project_json(sb3_file, extract_to):
    with zipfile.ZipFile(sb3_file, "r") as zip_ref:
        zip_ref.extract("project.json", extract_to)
        # Extract other files (excluding project.json)
        for file in zip_ref.namelist():
            if file != "project.json":
                zip_ref.extract(file, extract_to)


def merge_json_files(input_folder, output_file):
    if not os.path.exists(input_folder):
        print(
            f"The specified folder path '{input_folder}' does not exist. Please check the path."
        )
        exit(1)

    merged_data = None
    temp_folder = os.path.join(input_folder, "temp_json")

    if not os.path.exists(temp_folder):
        os.makedirs(temp_folder)

    # Iterate through all files in the folder
    for filename in os.listdir(input_folder):
        if filename.endswith(".sb3"):
            sb3_file_path = os.path.join(input_folder, filename)
            try:
                extract_project_json(sb3_file_path, temp_folder)
                json_file_path = os.path.join(temp_folder, "project.json")
                with open(json_file_path, "r", encoding="utf-8") as json_file:
                    data = json.load(json_file)
            except (json.JSONDecodeError, UnicodeDecodeError, zipfile.BadZipFile) as e:
                print(
                    f"File {filename} is not a valid sb3 file or could not be extracted, skipping. Error: {e}"
                )
                continue

            # Ensure JSON file conforms to Scratch's sb3 format
            if "targets" not in data:
                print(f"File {filename} is missing 'targets' section, cannot merge.")
                continue

            # Initialize merged_data with the first project or merge variables and targets
            if merged_data is None:
                merged_data = data
            else:
                # Merge variables
                for key, value in data.get("variables", {}).items():
                    if key not in merged_data["variables"]:
                        merged_data["variables"][key] = value

                # Merge lists
                for key, value in data.get("lists", {}).items():
                    if key not in merged_data["lists"]:
                        merged_data["lists"][key] = value

                # Merge broadcasts
                for key, value in data.get("broadcasts", {}).items():
                    if key not in merged_data["broadcasts"]:
                        merged_data["broadcasts"][key] = value

                # Merge targets (sprites and stage)
                for target in data["targets"]:
                    if not target["isStage"]:
                        # Check if a sprite with the same name already exists, if so, replace it
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

    # Write merged data to new JSON file
    if merged_data is not None:
        with open(output_file, "w", encoding="utf-8") as output_json_file:
            json.dump(merged_data, output_json_file, indent=4, ensure_ascii=False)

    # Compress into new sb3 file
    new_sb3_path = os.path.join(input_folder, "all_merge.sb3")
    with zipfile.ZipFile(new_sb3_path, "w") as new_sb3:
        # Add merged project.json
        new_sb3.write(output_file, "project.json")
        # Add other resource files
        for root, _, files in os.walk(temp_folder):
            for file in files:
                if file != "project.json":
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_folder)
                    new_sb3.write(file_path, arcname)

    # Clean up temp folder
    if os.path.exists(temp_folder):
        for temp_file in os.listdir(temp_folder):
            os.remove(os.path.join(temp_folder, temp_file))
        os.rmdir(temp_folder)


def select_folder(entry):
    folder_selected = filedialog.askdirectory()
    if folder_selected:
        entry.delete(0, tk.END)
        entry.insert(0, folder_selected)
    return folder_selected


def start_merge(entry):
    input_folder = entry.get()
    if not input_folder:
        messagebox.showerror("Error", "Please select a folder containing .sb3 files.")
        return

    output_file = os.path.join(input_folder, "project.json")
    merge_json_files(input_folder, output_file)
    messagebox.showinfo(
        "Success",
        "All sb3 files have been merged into all_merge.sb3 in the selected folder.",
    )


def main():
    # GUI setup
    root = tk.Tk()
    root.title("SB3 Merger")
    root.geometry("400x200")

    input_folder_label = tk.Label(root, text="Select Folder with SB3 Files:")
    input_folder_label.pack(pady=10)

    input_folder_entry = tk.Entry(root, width=50)
    input_folder_entry.pack(pady=5)

    select_folder_button = tk.Button(
        root, text="選擇資料夾", command=lambda: select_folder(input_folder_entry)
    )
    select_folder_button.pack(pady=5)

    start_merge_button = tk.Button(
        root, text="開始合併", command=lambda: start_merge(input_folder_entry)
    )
    start_merge_button.pack(pady=20)

    root.mainloop()


if __name__ == "__main__":
    main()
