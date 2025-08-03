import base64
from io import BytesIO
from PIL import Image
import numpy as np
import torch
import cv2

CATEGORYNAMESPACE = 'OpenOutpaint-Serving'

def get_category(sub_dir = None):
    if sub_dir is None:
        return CATEGORYNAMESPACE
    else:
        return f"{CATEGORYNAMESPACE}/{sub_dir}"

def _strip_prefix(s: str, prefix: str) -> str:
    if s.startswith(prefix):
        return s[len(prefix) :]
    return s


def convert_color(image):
    if len(image.shape) > 2 and image.shape[2] >= 4:
        return cv2.cvtColor(image, cv2.COLOR_BGRA2RGB)
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

def base64_to_image(base64_str):
    base64_str = _strip_prefix(base64_str, "data:image/png;base64,")
    nparr = np.frombuffer(base64.b64decode(base64_str), np.uint8)
    result = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)
    result = convert_color(result)
    result = result.astype(np.float32) / 255.0
    image = torch.from_numpy(result)[None,]
    return image

def base64_to_mask(base64_str):
    base64_str = _strip_prefix(base64_str, "data:image/png;base64,")
    nparr = np.frombuffer(base64.b64decode(base64_str), np.uint8)
    result = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)
    result = result.astype(np.float32) / 255.0
    image = torch.from_numpy(result)
    if image.dim() == 3:  # RGB(A) input, use red channel
        image = image[:, :, 0]
    return image.unsqueeze(0)

def image_to_base64(image):
    img_np = (image.cpu().numpy() * 255).astype('uint8')
    img_bytes = BytesIO()
    Image.fromarray(img_np.squeeze()).save(img_bytes, format='PNG')
    base64_image = base64.b64encode(img_bytes.getvalue()).decode('utf-8')
    return base64_image

def images_to_base64(images):
    base64_images = []
    for image in images:
        base64_image = image_to_base64(image)
        base64_images.append(base64_image)
    return base64_images

def preview_to_base64(image):
    img_bytes = BytesIO()
    image.save(img_bytes, format="JPEG", quality=80)
    base64_image = base64.b64encode(img_bytes.getvalue()).decode('utf-8')
    return base64_image

import json
def print_list_or_dic(header_str, data, test_json = False):
    output = ""
    output += f"\n========== {header_str}: start ==========\n"
    for key, value in enumerate(data) if type(data) is list else data.items():
        if key in ["images", "image", "mask", "init_images"]:
            truncated_value = str(value)[:30]
        else:
            truncated_value = str(value)[:500]
        output += f">    ({type(value)}) {key}: {truncated_value}\n"

    if test_json:
        try:
            j = json.dumps(data).encode('utf-8')
        except Exception as e:
            output += f"ERROR: {e}\ndata: <{type(data)}> {data}\n"

    output += f"========== {header_str}: end ==========\n"
    print(output)
