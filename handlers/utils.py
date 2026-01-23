

import io
import re
import qrcode


def is_valid_address(address: str, currency: str) -> bool:
    
    if not address or len(address) < 10:
        return False
        
    if currency == 'ltc':
        return is_valid_ltc_address(address)
    elif currency in ['usdt_bep20', 'usdt_polygon', 'ethereum']:
        
        return bool(re.match(r'^0x[a-fA-F0-9]{40}$', address))
    elif currency == 'solana':
        
        return bool(re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', address))
    return False


def is_valid_ltc_address(address: str) -> bool:
    
    if not address:
        return False
    
    legacy_pattern = r'^[LM][a-km-zA-HJ-NP-Z1-9]{26,33}$'
    segwit_pattern = r'^ltc1[a-zA-HJ-NP-Z0-9]{25,90}$'
    return bool(re.match(legacy_pattern, address) or re.match(segwit_pattern, address))


def get_explorer_url(currency: str, tx_hash: str) -> str:
    
    explorers = {
        'ltc': f"https://blockchair.com/litecoin/transaction/{tx_hash}",
        'usdt_bep20': f"https://bscscan.com/tx/{tx_hash}",
        'usdt_polygon': f"https://polygonscan.com/tx/{tx_hash}",
        'ethereum': f"https://etherscan.io/tx/{tx_hash}",
        'solana': f"https://solscan.io/tx/{tx_hash}"
    }
    return explorers.get(currency, f"https://blockchain.com/tx/{tx_hash}")


async def generate_qr_bytes(text):
    
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(text)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        byte_io = io.BytesIO()
        img.save(byte_io, 'PNG')
        byte_io.seek(0)
        
        return byte_io.getvalue()
    except Exception as e:
        print(f"QR generation error: {e}")
        return None
