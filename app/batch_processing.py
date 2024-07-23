import json
from pathlib import Path
from typing import Dict, Optional

import cv2
import numpy as np
from PIL import Image
from loguru import logger
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TimeElapsedColumn,
    MofNCompleteColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)

from app.helper import pil_to_bytes
from app.model.utils import torch_gc
from app.model_manager import ModelManager
from app.schema import InpaintRequest


def glob_images(path: Path) -> Dict[str, Path]:
    # png/jpg/jpeg
    if path.is_file():
        return {path.stem: path}
    elif path.is_dir():
        res = {}
        for it in path.glob("*.*"):
            if it.suffix.lower() in [".png", ".jpg", ".jpeg"]:
                res[it.stem] = it
        return res

def find_first_matching(arr, condition):
    for item in arr:
        if condition(item):
            return item
    return None

def batch_inpaint(
    model: str,
    device,
    image: Path,
    mask: Path,
    output: Path,
    config: Optional[Path] = None,
    concat: bool = False,
):
    if image.is_dir() and output.is_file():
        logger.error(
            "invalid --output: when image is a directory, output should be a directory"
        )
        exit(-1)
    output.mkdir(parents=True, exist_ok=True)

    image_paths = glob_images(image)
    mask_paths = glob_images(mask)
    if len(image_paths) == 0:
        logger.error("invalid --image: empty image folder")
        exit(-1)
    if len(mask_paths) == 0:
        logger.error("invalid --mask: empty mask folder")
        exit(-1)

    if config is None:
        inpaint_request = InpaintRequest()
        logger.info(f"Using default config: {inpaint_request}")
    else:
        with open(config, "r", encoding="utf-8") as f:
            inpaint_request = InpaintRequest(**json.load(f))
    model_manager = ModelManager(name=model, device=device)
    first_mask = list(mask_paths.values())[0]

    console = Console()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    ) as progress:
        task = progress.add_task("Batch processing...", total=len(image_paths))
        for stem, image_p in image_paths.items():
            infos = Image.open(image_p).info
            img = np.array(Image.open(image_p).convert("RGB"))
            # get same size mask
            m = find_first_matching(
                    mask_paths.values(),
                    lambda x: np.array(Image.open(x).convert("L")).shape[:2] == img.shape[:2]
                )
            # get mask.png
            mask_m = find_first_matching(
                    mask_paths.values(),
                    lambda x: x.name == 'mask.png'
                )
            if stem in mask_paths and mask.is_dir():
                mask_p = mask_paths.get(stem, first_mask)
                mask_img = np.array(Image.open(mask_p).convert("L"))
                progress.log('used same name mask')
            elif m and mask.is_dir():
                mask_p = m
                mask_img = np.array(Image.open(mask_p).convert("L"))
                progress.log('used same size mask')
            elif mask_m and mask.is_dir():
                mask_p = mask_m
                mask_img = np.array(Image.open(mask_p).convert("L"))
                progress.log('used mask.png')
            elif first_mask and not mask.is_dir():
                mask_p = mask_paths.get(stem, first_mask)
                mask_img = np.array(Image.open(mask_p).convert("L"))
                progress.log(f'used {mask_p.name}')
            else:
                progress.log(f"mask for {image_p} not found")
                progress.update(task, advance=1)
                continue

            if mask_img.shape[:2] != img.shape[:2]:
                progress.log(f"resize mask {mask_p.name} to image {image_p.name} size: {img.shape[:2]}")
                mask_img = cv2.resize(
                    mask_img,
                    (img.shape[1], img.shape[0]),
                    interpolation=cv2.INTER_NEAREST,
                )
            mask_img[mask_img >= 127] = 255
            mask_img[mask_img < 127] = 0

            # bgr
            inpaint_result = model_manager(img, mask_img, inpaint_request)
            inpaint_result = cv2.cvtColor(inpaint_result, cv2.COLOR_BGR2RGB)
            if concat:
                mask_img = cv2.cvtColor(mask_img, cv2.COLOR_GRAY2RGB)
                inpaint_result = cv2.hconcat([img, mask_img, inpaint_result])

            img_format = image_p.suffix.lower().lstrip(".")
            img_bytes = pil_to_bytes(Image.fromarray(inpaint_result), img_format, 85, infos)
            save_p = output / f"{stem}.{img_format}"
            with open(save_p, "wb") as fw:
                fw.write(img_bytes)

            progress.update(task, advance=1)
            torch_gc()
