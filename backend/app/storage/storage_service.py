import os
import shutil
from typing import BinaryIO
from loguru import logger
from app.storage.base_storage import BaseStorage

class LocalStorageService(BaseStorage):
    def __init__(self, upload_dir: str = "./local_storage"):
        self.upload_dir = upload_dir
        os.makedirs(self.upload_dir, exist_ok=True)
        logger.info(f"Local storage service initialized at directory: {self.upload_dir}")

    def save(self, file_stream: BinaryIO, filename: str) -> str:
        target_path = os.path.join(self.upload_dir, filename)
        logger.info(f"Saving file {filename} to {target_path}...")
        
        # Write binary stream to file
        with open(target_path, "wb") as f_out:
            shutil.copyfileobj(file_stream, f_out)
            
        logger.info(f"File {filename} successfully saved to {target_path}")
        return target_path

    def delete(self, filename: str) -> bool:
        target_path = os.path.join(self.upload_dir, filename)
        if os.path.exists(target_path):
            logger.info(f"Deleting local file: {target_path}...")
            os.remove(target_path)
            return True
        logger.warning(f"File not found for deletion: {target_path}")
        return False
