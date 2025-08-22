import os
import io
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from generator import generate_ad_ideas
from utils import make_placeholder_image

load_dotenv()

st.set_page_config(page_title="Ad Creative Idea Generator", page_icon="✨")
st.title("✨ Ad Creative Idea Generator")

with st.form("inputs"):
    col1, col2 = st.columns(2)
    product_name = col1.text_input("Product name", placeholder="GlowUp Serum")
    platform = col2.selectbox("Platform", ["Instagram", "Facebook Ads", "LinkedIn", "Google Ads", "TikTok"])
    product_description = st.text_area(
        "Product description",
        placeholder="Vitamin C + hyaluronic acid serum that brightens and hydrates in 7 days."
    )
    audience = st.text_input("Target audience", placeholder="Busy women 25-35 with sensitive skin")
    tone = st.selectbox("Tone / style", ["Friendly", "Bold", "Professional", "Playful", "Luxury", "Minimal"])
    num_ideas = st.slider("How many ad ideas?", min_value=3, max_value=10, value=5)
    generate_real_images = st.checkbox("Generate real images via OpenAI (may cost tokens)", value=False)
    submitted = st.form_submit_button("Generate ideas")

if submitted:
    if not product_name or not product_description or not audience:
        st.warning("Please fill product name, description, and audience.")
        st.stop()

    with st.spinner("Generating ad ideas..."):
        data = generate_ad_ideas(product_name, product_description, audience, tone, platform, num_ideas, generate_images=generate_real_images)

    # Create a table view
    df = pd.DataFrame({
        "Headline": data["headlines"],
        "Primary Text": data["primary_text"],
        "CTA": data["ctas"],
        "Visual Prompt": data["visual_prompts"],
    })
    st.subheader("Results")
    st.dataframe(df, use_container_width=True)

    # Present as expanders/cards with images
    st.subheader("Ideas (detailed)")
    image_files = data.get("image_files", [])
    outdir = "generated_images"
    os.makedirs(outdir, exist_ok=True)
    for i in range(num_ideas):
        with st.expander(f"Idea {i+1}: {data['headlines'][i]}", expanded=(i==0)):
            st.markdown(f"**Headline:** {data['headlines'][i]}")
            st.markdown(f"**Copy:** {data['primary_text'][i]}")
            st.markdown(f"**CTA:** {data['ctas'][i]}")
            st.markdown(f"**Visual prompt:** {data['visual_prompts'][i]}")

            # decide image path: real image if generated, else creating placeholder
            img_path = None
            if len(image_files) >= (i+1):
                img_path = image_files[i]
            else:
                # creating placeholder image file
                placeholder_path = os.path.join(outdir, f"placeholder_{i+1}.png")
                make_placeholder_image(f"{product_name}\n{data['visual_prompts'][i]}", placeholder_path)
                img_path = placeholder_path

            st.image(img_path, use_column_width=True)

    # CSV + zip of images
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", data=csv, file_name="ad_ideas.csv", mime="text/csv")

    # creating zip of images
    import zipfile
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # include any generated images + placeholders in folder
        for fname in sorted(os.listdir(outdir)):
            fpath = os.path.join(outdir, fname)
            zf.write(fpath)
    st.download_button("Download images (ZIP)", data=zip_buf.getvalue(), file_name="ad_creatives.zip", mime="application/zip")

st.markdown("---")
