import json
import os
from glob import glob
from PIL import Image
import xml.etree.ElementTree as ET
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


# open json file
def parse_tmj_file(tmj_path):
    with open(tmj_path, "r") as file:
        tmj_data = json.load(file)
    return tmj_data


def segment_tileset_image(
    tileset_image_path, output_dir, first_gid, tile_width, tile_height
):
    image = Image.open(tileset_image_path)
    img_width, img_height = image.size

    cols = img_width // tile_width
    rows = img_height // tile_height

    for row in range(rows):
        for col in range(cols):
            left = col * tile_width
            upper = row * tile_height
            right = left + tile_width
            lower = upper + tile_height

            # Ensure the cropping dimensions are within the image bounds
            right = min(right, img_width)
            lower = min(lower, img_height)

            tile_gid = first_gid + row * cols + col
            tile = image.crop((left, upper, right, lower))
            tile_output_path = os.path.join(output_dir, f"tile_{tile_gid}.png")
            tile.save(tile_output_path)


def extract_and_name_tiles_from_layer(layer_data, tilesets, output_dir):
    for tile_index, gid in enumerate(layer_data):
        if gid == 0:
            continue

        tileset = next(
            ts
            for ts in tilesets
            if ts["firstgid"] <= gid < ts["firstgid"] + ts["tile_count"]
        )
        tile_id = gid - tileset["firstgid"]
        tile_output_path = os.path.join(
            output_dir, f"layer_tile_{tile_index}_gid_{gid}.png"
        )

        # Assuming the tiles are already saved as individual images
        tileset_output_dir = os.path.join(output_dir, f'tileset_{tileset["firstgid"]}')
        tile_image_path = os.path.join(tileset_output_dir, f"tile_{gid}.png")

        if os.path.exists(tile_image_path):
            tile = Image.open(tile_image_path)
            tile.save(tile_output_path)


def search_output_folder(tmj_data):
    current_folder = os.getcwd()
    all_files = os.listdir(current_folder)

    # Step 1: Look for the folder containing output images
    output_folder_image = None
    output_folder_path = None
    for file in all_files:
        if "output" in file and os.path.isdir(file):
            output_folder_image = os.listdir(file)
            output_folder_path = os.path.join(current_folder, file)
            break
        else:
            print("No output folder found.")

    if not output_folder_image:
        return  # Exit the function if no output folder is found

    # Step 2: Create a folder called "used" to move matched images into
    used_folder_path = os.path.join(current_folder, "裁切好的圖片")
    os.makedirs(used_folder_path, exist_ok=True)

    # Step 3: Extract the tile number from image names in the output folder
    image_number_mapping = {}
    for image in output_folder_image:
        if image.startswith("tile_") and image.endswith(".png"):
            # Extract the number from the image name (e.g., "tile_1.png" -> 1)
            tile_number = int(image.split("_")[1].split(".")[0])
            image_number_mapping[tile_number] = image

    # Step 4: Loop through the layers in tmj_data and match tile numbers
    for layer in tmj_data["layers"]:
        print(layer["data"])
        if layer["type"] == "tilelayer":
            for tile_number in layer["data"]:
                # Match the tile number with the corresponding image
                if tile_number in image_number_mapping:
                    image_name = image_number_mapping[tile_number]
                    image_path = os.path.join(output_folder_path, image_name)
                    new_path = os.path.join(used_folder_path, image_name)
                    shutil.move(image_path, new_path)
                    print(f"Moved {image_name} to used folder.")

    # Step 5: After moving all images, delete the output folder
    if len(os.listdir(used_folder_path)) != 0:
        shutil.rmtree(output_folder_path)
        print(f"Deleted output folder: {output_folder_path}")
    else:
        print(f"Some files remain in the output folder: {output_folder_path}")


def process_tmj_files(folder_path):
    os.chdir(folder_path)

    # Get all TMJ files in the selected directory
    tmj_files = glob("*.tmj")
    if not tmj_files:
        print("No TMJ files found in the selected directory.")
        return

    # Process each TMJ file
    for tmj_path in tmj_files:
        # Parse TMJ file
        tmj_data = parse_tmj_file(tmj_path)

        output_dir = os.path.join(os.getcwd(), "output")

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Iterate through all tilesets in the TMJ data
        tilesets = []
        for tileset in tmj_data["tilesets"]:
            first_gid = tileset["firstgid"]
            source = tileset["source"]

            # Load the TSX (tileset) file
            tsx_path = os.path.join(os.path.dirname(tmj_path), source)
            if not os.path.exists(tsx_path):
                print(f"Error: TSX file '{tsx_path}' not found.")
                continue

            # Parse TSX file as XML
            tree = ET.parse(tsx_path)
            root = tree.getroot()

            # Get image path from TSX file
            image_source = root.find("image").get("source")
            tileset_image_path = os.path.join(os.path.dirname(tsx_path), image_source)

            if not os.path.exists(tileset_image_path):
                print(f"Error: Tileset image file '{tileset_image_path}' not found.")
                continue

            # Get tile dimensions from the TSX file
            tile_width = int(root.get("tilewidth"))
            tile_height = int(root.get("tileheight"))

            # Segment the tileset image and save tiles
            segment_tileset_image(
                tileset_image_path, output_dir, first_gid, tile_width, tile_height
            )

            # Store tileset information for further processing
            tilesets.append(
                {
                    "firstgid": first_gid,
                    "tile_count": (Image.open(tileset_image_path).size[0] // tile_width)
                    * (Image.open(tileset_image_path).size[1] // tile_height),
                }
            )

        # Extract and name tiles from layer data
        for layer in tmj_data["layers"]:
            if layer["type"] == "tilelayer":
                extract_and_name_tiles_from_layer(layer["data"], tilesets, output_dir)

        search_output_folder(tmj_data)


def main():
    # Create the main window
    root = tk.Tk()
    root.title("Tiled Editor 圖片分割工具")
    root.geometry("400x200")
    root.configure(bg="#f0f0f0")

    selected_folder = tk.StringVar()

    def select_folder():
        folder_path = filedialog.askdirectory()
        if folder_path:
            selected_folder.set(folder_path)

    def start_processing():
        folder_path = selected_folder.get()
        if not folder_path:
            messagebox.showerror("錯誤", "請選擇一個資料夾。")
            return

        process_tmj_files(folder_path)
        messagebox.showinfo("完成", "處理成功完成。")

    # Create a frame for content
    content_frame = ttk.Frame(root, padding=(20, 10))
    content_frame.grid(row=0, column=0, sticky=("N", "S", "E", "W"))

    # Create GUI elements
    ttk.Label(content_frame, text="注意! 選擇包含地圖的 Tiled Editor 專案資料夾:").grid(
        row=0, column=0, columnspan=2, pady=(0, 10)
    )

    select_button = ttk.Button(content_frame, text="選擇資料夾", command=select_folder)
    select_button.grid(row=1, column=0, pady=10, sticky="W")

    folder_entry = ttk.Entry(
        content_frame, textvariable=selected_folder, width=30, state="readonly"
    )
    folder_entry.grid(row=1, column=1, padx=10, pady=10, sticky="E")

    start_button = ttk.Button(content_frame, text="開始處理", command=start_processing)
    start_button.grid(row=2, column=0, columnspan=2, pady=20)

    # Configure resizing behavior
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    content_frame.columnconfigure(1, weight=1)

    # Run the main loop
    root.mainloop()


if __name__ == "__main__":
    main()
