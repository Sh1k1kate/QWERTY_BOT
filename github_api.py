import aiohttp
import base64
import json
from config import GITHUB_TOKEN, OWNER, REPO

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}
BASE_URL = f"https://api.github.com/repos/{OWNER}/{REPO}/contents"

async def get_file_content(file_path: str):
    url = f"{BASE_URL}/{file_path}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=HEADERS) as resp:
            if resp.status == 200:
                data = await resp.json()
                content = base64.b64decode(data["content"]).decode("utf-8")
                return json.loads(content)
            elif resp.status == 404:
                return None
            else:
                text = await resp.text()
                raise Exception(f"GitHub GET error {resp.status}: {text}")

async def save_file_content(file_path: str, data: dict, message: str = "Update from bot"):
    url = f"{BASE_URL}/{file_path}"
    sha = None
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=HEADERS) as resp:
            if resp.status == 200:
                sha = (await resp.json())["sha"]

    content = base64.b64encode(
        json.dumps(data, indent=2, ensure_ascii=False).encode()
    ).decode()

    payload = {
        "message": message,
        "content": content,
        "branch": "main"
    }
    if sha:
        payload["sha"] = sha

    async with aiohttp.ClientSession() as session:
        async with session.put(url, headers=HEADERS, json=payload) as resp:
            if resp.status not in (200, 201):
                text = await resp.text()
                raise Exception(f"GitHub PUT error {resp.status}: {text}")
    return True
