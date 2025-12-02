import aiohttp
import asyncio
import logging
import os
import sys
import zipfile
import shutil
from typing import Optional, Dict, Any

logger = logging.getLogger("StarVell.updater")

GITHUB_REPO = "abuzedr/StarvellNexusBot"
GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


class Updater:
    def __init__(self, current_version: str, github_token: Optional[str] = None):
        self.current_version = current_version
        self.github_token = github_token
        self.latest_version: Optional[str] = None
        self.download_url: Optional[str] = None
        self.changelog: Optional[str] = None
    
    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "StarvellNexus-Bot"
        }
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"
        return headers
    
    async def check_updates(self) -> Dict[str, Any]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    GITHUB_API, 
                    headers=self._get_headers(),
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    if resp.status == 404:
                        return {"available": False, "error": "Репозиторий не найден"}
                    if resp.status == 401:
                        return {"available": False, "error": "Неверный GitHub токен"}
                    if resp.status != 200:
                        return {"available": False, "error": f"HTTP {resp.status}"}
                    
                    data = await resp.json()
                    self.latest_version = data.get("tag_name", "").lstrip("v")
                    self.changelog = data.get("body", "")
                    
                    for asset in data.get("assets", []):
                        if asset.get("name", "").endswith(".zip"):
                            self.download_url = asset.get("browser_download_url")
                            break
                    
                    if not self.download_url:
                        self.download_url = data.get("zipball_url")
                    
                    if self._is_newer(self.latest_version, self.current_version):
                        return {
                            "available": True,
                            "version": self.latest_version,
                            "download_url": self.download_url,
                            "changelog": self.changelog[:500] if self.changelog else ""
                        }
                    
                    return {"available": False, "version": self.current_version}
                    
        except asyncio.TimeoutError:
            return {"available": False, "error": "Таймаут соединения"}
        except Exception as e:
            logger.debug(f"Update check failed: {e}")
            return {"available": False, "error": str(e)}
    
    def _is_newer(self, latest: str, current: str) -> bool:
        try:
            def parse_version(v):
                return [int(x) for x in v.replace("-", ".").split(".")[:3]]
            return parse_version(latest) > parse_version(current)
        except Exception:
            return False
    
    async def auto_update(self) -> bool:
        if not self.download_url or not self.latest_version:
            logger.error("❌ Нет URL для скачивания")
            return False
        
        try:
            logger.info(f"📥 Скачиваю обновление v{self.latest_version}...")
            
            temp_zip = "update_temp.zip"
            temp_dir = "update_temp"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.download_url, 
                    headers=self._get_headers(),
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as resp:
                    if resp.status != 200:
                        logger.error(f"❌ Ошибка скачивания: HTTP {resp.status}")
                        return False
                    
                    content = await resp.read()
                    
                    with open(temp_zip, "wb") as f:
                        f.write(content)
            
            logger.info("📦 Распаковываю...")
            
            with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            extracted_dirs = [d for d in os.listdir(temp_dir) if os.path.isdir(os.path.join(temp_dir, d))]
            if not extracted_dirs:
                logger.error("❌ Пустой архив")
                return False
            
            source_dir = os.path.join(temp_dir, extracted_dirs[0])
            
            PROTECTED = {"configs", "storage", "logs", "plugins/data", ".git"}
            
            logger.info("🔄 Обновляю файлы...")
            
            for item in os.listdir(source_dir):
                if item in PROTECTED:
                    continue
                    
                src = os.path.join(source_dir, item)
                dst = item
                
                try:
                    if os.path.isdir(src):
                        if os.path.exists(dst):
                            shutil.rmtree(dst, ignore_errors=True)
                        shutil.copytree(src, dst, dirs_exist_ok=True)
                    else:
                        shutil.copy2(src, dst)
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось обновить {item}: {e}")
            
            os.remove(temp_zip)
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            logger.info(f"✅ Обновление до v{self.latest_version} установлено!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка автообновления: {e}")
            if os.path.exists("update_temp.zip"):
                os.remove("update_temp.zip")
            if os.path.exists("update_temp"):
                shutil.rmtree("update_temp", ignore_errors=True)
            return False
    
    @staticmethod
    def restart_bot():
        logger.info("🔄 Перезапуск бота...")
        python = sys.executable
        os.execl(python, python, *sys.argv)
