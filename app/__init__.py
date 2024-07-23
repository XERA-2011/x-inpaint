import os

os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
# https://github.com/pytorch/pytorch/issues/27971#issuecomment-1768868068
os.environ["ONEDNN_PRIMITIVE_CACHE_CAPACITY"] = "1"
os.environ["LRU_CACHE_CAPACITY"] = "1"
# prevent CPU memory leak when run model on GPU
# https://github.com/pytorch/pytorch/issues/98688#issuecomment-1869288431
# https://github.com/pytorch/pytorch/issues/108334#issuecomment-1752763633
os.environ["TORCH_CUDNN_V8_API_LRU_CACHE_LIMIT"] = "1"

import warnings

from app.config import CONFIG

warnings.simplefilter("ignore", UserWarning)


def entry_point():
    # To make os.environ["XDG_CACHE_HOME"] = args.model_cache_dir works for diffusers
    # https://github.com/huggingface/diffusers/blob/be99201a567c1ccd841dc16fb24e88f7f239c187/src/diffusers/utils/constants.py#L18
    from app.cli import typer_app

    # python main.py run --model=lama --device=cpu --image=image_folder --mask=mask_folder --output=output_dir
    command_args = [
        "run",
        "--model", CONFIG['model'],
        "--device", CONFIG['device'],
        "--image", CONFIG['image'],
        "--mask", CONFIG['mask'],
        "--output", CONFIG['output'],
    ]
    typer_app(command_args)