import os
import glob
import nbformat as nbf

def build_notebook():
    nb = nbf.v4.new_notebook()
    cells = [
        nbf.v4.new_markdown_cell('# Member 1 — Exploratory Data Analysis (EDA)\nThis notebook performs initial inspection, structural validation, and feature distribution checks on the raw datasets:\n1. **Squirrel-Cage Induction Motor Fault Diagnosis Dataset**\n2. **MetroPT-3 Multivariate Sensor Dataset**\n3. **Thermal Image Dataset for Induction Motors**'),
        
        nbf.v4.new_code_cell('''import os
import glob
import pandas as pd
import numpy as np
from PIL import Image

print('Pandas version:', pd.__version__)
print('Numpy version:', np.__version__)
'''),

        nbf.v4.new_markdown_cell('## 1. MetroPT-3 Dataset Inspection'),
        nbf.v4.new_code_cell('''metro_csv = os.path.join('..', 'data', 'raw', 'metropt3', 'MetroPT3(AirCompressor).csv')
if os.path.exists(metro_csv):
    df_metro = pd.read_csv(metro_csv, nrows=5000)
    print("MetroPT3 Columns:", df_metro.columns.tolist())
    print("Sample Shape:", df_metro.shape)
    display(df_metro.head())
    display(df_metro.describe())
else:
    print("MetroPT3 raw CSV not found at expected path.")
'''),

        nbf.v4.new_markdown_cell('## 2. Thermal Image Dataset Inspection'),
        nbf.v4.new_code_cell('''thermal_dir = os.path.join('..', 'data', 'raw', 'thermal_motor')
thermal_files = glob.glob(os.path.join(thermal_dir, '**', '*.png'), recursive=True)
print(f"Total Thermal Motor Frames Found: {len(thermal_files)}")

if thermal_files:
    sample_img_path = thermal_files[0]
    with Image.open(sample_img_path) as img:
        img_arr = np.array(img)
        print("Sample Thermal Image Mode:", img.mode)
        print("Sample Thermal Image Size:", img.size)
        print("Sample Thermal Pixel Range:", img_arr.min(), "to", img_arr.max())
'''),

        nbf.v4.new_markdown_cell('## 3. Squirrel-Cage Induction Motor Dataset Inspection'),
        nbf.v4.new_code_cell('''squirrel_dir = os.path.join('..', 'data', 'raw', 'squirrel_cage')
squirrel_files = glob.glob(os.path.join(squirrel_dir, '**', '*.png'), recursive=True)
print(f"Total Squirrel-Cage Frames Found: {len(squirrel_files)}")

if squirrel_files:
    sample_sq_path = squirrel_files[0]
    with Image.open(sample_sq_path) as img:
        img_arr = np.array(img)
        print("Sample Squirrel Image Mode:", img.mode)
        print("Sample Squirrel Image Size:", img.size)
        print("Sample Squirrel Pixel Range:", img_arr.min(), "to", img_arr.max())
''')
    ]
    nb['cells'] = cells
    
    target_path = os.path.join('notebooks', 'member1_eda.ipynb')
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    with open(target_path, 'w', encoding='utf-8') as f:
        nbf.write(nb, f)
    print(f"Notebook created at {target_path}")

if __name__ == '__main__':
    build_notebook()
