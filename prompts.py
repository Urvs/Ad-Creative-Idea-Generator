# prompts.py
PROMPT_TEMPLATE = """
You are an expert creative strategist and ad copywriter.
Generate {num_ideas} unique ad creative ideas for the product below.

Product: {product_name}
Description: {product_description}
Audience: {audience}
Tone: {tone}
Platform: {platform}

Return STRICT JSON only with these keys and exactly {num_ideas} items in each list:

{{
  "headlines": ["..."],            // list of {num_ideas} short headlines (<= 60 chars)
  "primary_text": ["..."],         // list of {num_ideas} 1-2 sentence ad copies (each distinct)
  "ctas": ["..."],                 // list of {num_ideas} short CTAs (each distinct)
  "visual_prompts": ["..."]        // list of {num_ideas} short visual prompts suitable for image generation (each distinct)
}}

Requirements:
- All items in each list MUST be distinct from one another.
- Make ideas varied in style (emotional, humorous, minimalist, bold, aspirational, data-driven).
- Do NOT include any commentary or explanation outside of the single JSON object.
- If you cannot fill every slot, still return an array of length {num_ideas} and leave empty strings for missing items.
"""
