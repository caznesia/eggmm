import io
import asyncio
from PIL import Image, ImageDraw, ImageOps, ImageFont
import aiohttp
import base64
import logging
import config

logger = logging.getLogger(__name__)



SHIELD_ICON_B64 = "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"

async def generate_handshake_image(buyer_pfp, seller_pfp):
    
    async def fetch_asset(url_or_bytes, session):
        if not url_or_bytes: return None
        if not isinstance(url_or_bytes, str): return url_or_bytes
        try:
            
            headers = {'User-Agent': 'Mozilla/5.0 (RainyDay Bot)'}
            async with session.get(url_or_bytes, timeout=10, headers=headers) as resp:
                if resp.status == 200:
                    return await resp.read()
                logger.error(f"[FETCH_ERR] Status {resp.status} for {url_or_bytes}")
        except Exception as e:
            logger.error(f"[FETCH_EXC] Error fetching {url_or_bytes}: {e}")
        return None

    async with aiohttp.ClientSession() as session:
        buyer_bytes = await fetch_asset(buyer_pfp, session)
        seller_bytes = await fetch_asset(seller_pfp, session)
        
        
        shield_url = config.VERIFIED_ICON_URL
        shield_bytes = await fetch_asset(shield_url, session)

    return await asyncio.to_thread(_generate_sync, buyer_bytes, seller_bytes, shield_bytes)

def _generate_sync(buyer_bytes, seller_bytes, shield_bytes=None):
    
    W, H = 800, 250
    bg_color = config.BANNER_BG_COLOR
    line_color = config.BANNER_THEME_COLOR
    
    
    img = Image.new('RGBA', (W, H), bg_color)
    draw = ImageDraw.Draw(img)
    
    
    draw.line([(200, H//2), (600, H//2)], fill=line_color, width=6)
    
    
    def process_avatar(bytes_data):
        try:
            pfp = Image.open(io.BytesIO(bytes_data)).convert("RGBA")
            pfp = pfp.resize((150, 150), Image.Resampling.LANCZOS)
            
            
            mask = Image.new("L", (150, 150), 0)
            draw_mask = ImageDraw.Draw(mask)
            draw_mask.ellipse((0, 0, 150, 150), fill=255)
            
            output = ImageOps.fit(pfp, mask.size, centering=(0.5, 0.5))
            output.putalpha(mask)
            return output
        except:
            
            return Image.new('RGBA', (150, 150), (100, 100, 100))

    buyer_img = process_avatar(buyer_bytes)
    seller_img = process_avatar(seller_bytes)
    
    
    img.paste(buyer_img, (50, 50), buyer_img)
    img.paste(seller_img, (600, 50), seller_img)
    
    
    if shield_bytes:
        try:
            shield = Image.open(io.BytesIO(shield_bytes)).convert("RGBA")
            shield = shield.resize((80, 80), Image.Resampling.LANCZOS)
            
            
            sx = (W - 80) // 2
            sy = (H - 80) // 2
            img.paste(shield, (sx, sy), shield)
        except Exception as e:

            logger.error(f"Shield error: {e}")

    
    try:
        
        draw.text(((W//2)-30, sy + 90), "SECURED", fill=line_color, font_size=16)
    except: pass

    
    final_buffer = io.BytesIO()
    img.save(final_buffer, format='PNG')
    final_buffer.seek(0)
    return final_buffer
