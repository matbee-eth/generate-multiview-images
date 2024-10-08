# generate-multiview-images

This project provides a set of tools to generate multi-view images from STL files using Blender. The script processes STL files, arranges the parts, sets up the scene, and renders images from multiple views. The final output includes a composite image showing different views of the 3D model. The goal is to train a diffusion model, like FLUX, to generate multiview images of articulating 3d models.

## Features

- Import STL files
- Separate loose parts in the STL
- Setup materials for the parts
- Arrange parts along the primary axis
- Setup lighting and scene for rendering
- Render images from multiple views
- Assemble a composite image from the rendered views

## Requirements

- Blender
- Python
- Pillow (PIL)

## Installation

1. **Blender**: Ensure Blender is installed on your system. You can download it from [Blender's official website](https://www.blender.org/download/).

2. **Python**: Ensure Python is installed on your system. You can download it from [Python's official website](https://www.python.org/downloads/).

3. **Pillow**: Install the Pillow library using pip:
   ```sh
   pip install pillow
   ```

## Usage

1. **Prepare the Directory Structure**:
   - Place your STL files in a directory named `File` or `Files`.
   - Place your main image in a directory named `IMG`.

2. **Run the Script**:
   ```sh
       ./blender-4.2.1-linux-x64/blender --background --python ./merged.py
   ```

3. **Script Execution**:
   - The script will process each STL file in the `File` or `Files` directory.
   - It will generate images from multiple views and save them in the same directory.
   - It will also create a composite image and save it in the parent directory.

## Example

Assuming your base path is `/mnt/data/stls`, the directory structure should look like this:

Here is an example of the output images arranged in a grid:

<table>
  <tr>
    <td><img src="images/front_view.png" alt="Front View" width="200"/></td>
    <td><img src="images/back_view.png" alt="Back View" width="200"/></td>
    <td><img src="images/left_view.png" alt="Left View" width="200"/></td>
  </tr>
  <tr>
    <td><img src="images/right_view.png" alt="Right View" width="200"/></td>
    <td><img src="images/top_view.png" alt="Top View" width="200"/></td>
    <td><img src="images/bottom_view.png" alt="Bottom View" width="200"/></td>
  </tr>
</table>
