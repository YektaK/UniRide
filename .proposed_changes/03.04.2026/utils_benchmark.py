import os
import json
import hashlib
from typing import Dict, Any, List

def get_file_hash(filepath: str) -> str:
    """Belirtilen dosyanın SHA-256 özetini (hash) döndürür."""
    if not os.path.exists(filepath):
        return ""
    
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def get_latest_metadata(metadata_path: str) -> Dict[str, Any]:
    """Test geçmişi tutulan JSON metadata dosyasını okur."""
    if not os.path.exists(metadata_path):
        # Default template
        return {
            "file_hashes": {}, 
            "results": {}, 
            "last_updated": ""
        }
    
    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {
            "file_hashes": {}, 
            "results": {}, 
            "last_updated": ""
        }

def save_metadata(metadata_path: str, data: Dict[str, Any]):
    """Güncel hash ve test sonuçlarını metadata JSON belgesine kaydeder."""
    os.makedirs(os.path.dirname(metadata_path), exist_ok=True)
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def check_algorithms_status(
    metadata: Dict[str, Any], 
    algorithms_to_check: Dict[str, str]
) -> Dict[str, str]:
    """
    Algoritmaların dosya hash'lerini güncel metadatadaki sürümle kıyaslar.
    Dönüş: 'YENI', 'DEGISMIS' veya 'GUNCEL'.
    Örn: algorithms_to_check = {'LinearSplitDecoder': 'optimizer_api/utils/linear_split_decoder.py'}
    """
    status_report = {}
    saved_hashes = metadata.get("file_hashes", {})
    
    for algo_name, filepath in algorithms_to_check.items():
        if not os.path.exists(filepath):
            status_report[algo_name] = "DOSYA_YOK"
            continue
            
        current_hash = get_file_hash(filepath)
        
        if algo_name not in saved_hashes:
            status_report[algo_name] = "YENI"
        elif saved_hashes[algo_name] != current_hash:
            status_report[algo_name] = "DEGISMIS"
        else:
            status_report[algo_name] = "GUNCEL"
            
    return status_report
