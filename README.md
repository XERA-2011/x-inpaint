# x-inpaint
> Batch processing for image inpainting.


> [IOPaint](https://github.com/Sanster/IOPaint)
> Here is the source code, which extracts the code for batch repairing images for secondary development.

## Usage

- image_folder
  + `the image that needs to be inpaint`

- mask_folder
  + `mask image`

- output_dir
  + `inpaint image`


## Development

```bash
pip install -r requirements.txt

# python main.py run --model=lama --device=cpu --image=image_folder --mask=mask_folder/mask.png --output=output_dir
python main.py
```

## Generate exe

```bash
pyinstaller --onefile main.py
```