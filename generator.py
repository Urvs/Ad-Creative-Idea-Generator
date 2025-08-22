import os
import json
import base64
import requests
from dotenv import load_dotenv
from prompts import PROMPT_TEMPLATE
from utils import extract_json, ensure_lists, make_unique_lists, make_placeholder_image

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
HF_API_TOKEN = os.getenv("HF_API_TOKEN")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
HF_MODEL = os.getenv("HF_MODEL", "mistralai/Mistral-7B-Instruct-v0.2")

def _openai_text_generate(prompt: str):
    try:
        from openai import OpenAI
    except Exception as e:
        raise RuntimeError("openai package not installed. Run: pip install openai") from e
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not set")
    client = OpenAI(api_key=OPENAI_API_KEY)
    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "You are a terse, high-converting ad copywriter."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.8,
        max_tokens=1200,
    )
    return resp.choices[0].message.content

def _hf_inference_generate(prompt: str):
    if not HF_API_TOKEN:
        raise RuntimeError("HF_API_TOKEN not set")
    url = f"https://api-inference.huggingface.co/models/{HF_MODEL}"
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
    data = {"inputs": prompt, "parameters": {"max_new_tokens": 512, "temperature": 0.7}}
    r = requests.post(url, headers=headers, json=data, timeout=120)
    r.raise_for_status()
    out = r.json()
    if isinstance(out, list) and len(out) and "generated_text" in out[0]:
        return out[0]["generated_text"]
    if isinstance(out, dict) and "generated_text" in out:
        return out["generated_text"]
    return json.dumps(out)

def _openai_generate_images(prompts, out_dir="generated_images", size="1024x1024"):
    """
    Try to generate images using OpenAI Image API.
    Returns list of file paths for created images. If not available or fails, raises.
    """
    try:
        from openai import OpenAI
    except Exception as e:
        raise RuntimeError("openai package not installed. Run: pip install openai") from e
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not set")

    client = OpenAI(api_key=OPENAI_API_KEY)
    os.makedirs(out_dir, exist_ok=True)
    image_paths = []
    for i, prompt in enumerate(prompts, start=1):
        try:
            # Attempt images.generate — API shape may differ across versions; handle common shapes.
            resp = client.images.generate(model="gpt-image-1", prompt=prompt, size=size)
            # resp may contain data[0].b64_json or data[0].url
            data = getattr(resp, "data", None) or resp.get("data", None) if isinstance(resp, dict) else None
            if data and len(data) and isinstance(data[0], dict):
                if "b64_json" in data[0]:
                    b64 = data[0]["b64_json"]
                    image_bytes = base64.b64decode(b64)
                elif "url" in data[0]:
                    # fetch the URL
                    url = data[0]["url"]
                    r = requests.get(url, timeout=30)
                    r.raise_for_status()
                    image_bytes = r.content
                else:
                    # unknown format
                    raise RuntimeError("Unknown image response format")
            else:
                # fallback for older client: resp.data[0].b64_json
                if isinstance(resp, dict) and "data" in resp and len(resp["data"]) and "b64_json" in resp["data"][0]:
                    b64 = resp["data"][0]["b64_json"]
                    image_bytes = base64.b64decode(b64)
                else:
                    raise RuntimeError("Image generation returned unexpected shape")

            path = os.path.join(out_dir, f"ai_creative_{i}.png")
            with open(path, "wb") as f:
                f.write(image_bytes)
            image_paths.append(path)
        except Exception as e:
            # any failure -> raise so caller can fallback to placeholders
            raise RuntimeError(f"Image generation failed for prompt #{i}: {e}")
    return image_paths

def _offline_generate(product_name, product_description, audience, tone, platform, num_ideas=5):
    benefits = [
        "save time every day", "look and feel great", "boost your results fast",
        "smarter choice for busy people", "designed for real life", "feel the difference"
    ]
    hooks = [
        "What if this took 5 minutes?", "No fluff. Just results.",
        "Small change, big impact.", "Your customers will thank you."
    ]
    ctabase = ["Try it now", "Get started", "Learn more", "Shop now", "Book a demo"]

    headlines = []
    primary = []
    ctas = []
    visuals = []

    for i in range(num_ideas):
        h = f"{product_name}: {benefits[i % len(benefits)].capitalize()}"
        p = f"{product_description} — {hooks[i % len(hooks)]}"
        c = ctabase[i % len(ctabase)]
        v = f"Minimal hero shot of {product_name} styled for {audience}, {tone} tone"
        headlines.append(h)
        primary.append(p)
        ctas.append(c)
        visuals.append(v)

    return {"headlines": headlines, "primary_text": primary, "ctas": ctas, "visual_prompts": visuals}

def generate_ad_ideas(product_name, product_description, audience, tone, platform, num_ideas=5, generate_images=False):
    """
    Returns dict with keys: headlines, primary_text, ctas, visual_prompts.
    If generate_images=True and OpenAI images succeed, adds "image_files": [local paths].
    """
    prompt = PROMPT_TEMPLATE.format(
        product_name=product_name.strip()[:200],
        product_description=product_description.strip()[:600],
        audience=audience.strip()[:200],
        tone=tone.strip()[:80],
        platform=platform.strip()[:80],
        num_ideas=num_ideas
    )

    raw = None
    if OPENAI_API_KEY:
        try:
            raw = _openai_text_generate(prompt)
        except Exception as e:
            print(f"[generator] OpenAI text generation failed: {e}")
            raw = None

    if raw is None and HF_API_TOKEN:
        try:
            raw = _hf_inference_generate(prompt)
        except Exception as e:
            print(f"[generator] HF generation failed: {e}")
            raw = None

    if raw is None:
        data = _offline_generate(product_name, product_description, audience, tone, platform, num_ideas)
    else:
        data = extract_json(raw)

    # Ensure lists exist & correct length
    data = ensure_lists(data, num_ideas)
    # Make items unique programmatically if model accidentally duplicated entries
    data = make_unique_lists(data, num_ideas)

    # Attempt image generation if requested
    image_files = []
    if generate_images:
        try:
            # use the visual_prompts as image prompts
            image_files = _openai_generate_images(data["visual_prompts"], out_dir="generated_images")
        except Exception as e:
            print(f"[generator] Image generation failed or not configured: {e}")
            image_files = []  # will be handled by caller (use placeholders)

    # attach image files if any
    if image_files:
        data["image_files"] = image_files

    return data
