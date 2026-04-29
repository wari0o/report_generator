import os
import requests

class ConfluencePublisher:
    def __init__(self, url, space_key, output_dir):
        self.url = url
        self.space_key = space_key
        self.output_dir = output_dir

    def check_auth(self, token):
        url = f"{self.url}/rest/api/user/current"
        headers = {"Authorization": f"Bearer {token}"}
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                user_data = response.json()
                print(f"✓ Авторизован как: {user_data['displayName']}")
                return True
            else:
                print(f"✗ Ошибка {response.status_code}: {response.text}")
                return False
        except Exception as e:
            print(f"✗ Ошибка подключения: {str(e)}")
            return False

    def create_page(self, token, parent_id, page_name, content):
        url = f"{self.url}/rest/api/content"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "type": "page",
            "title": page_name,
            "space": {"key": self.space_key},
            "ancestors": [{"id": parent_id}],
            "body": {
                "storage": {
                    "value": content,
                    "representation": "storage"
                }
            }
        }
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            page_data = response.json()
            print(f"✓ Страница создана: {page_data['_links']['webui']}")
            return page_data['id']
        except requests.exceptions.HTTPError as e:
            print(f"✗ HTTP ошибка: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            print(f"✗ Ошибка: {str(e)}")
        return None

    def upload_attachments(self, page_id, token):
        url = f"{self.url}/rest/api/content/{page_id}/child/attachment"
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Atlassian-Token": "no-check"
        }
        for filename in os.listdir(self.output_dir):
            if filename.lower().endswith('.png'):
                file_path = os.path.join(self.output_dir, filename)
                try:
                    with open(file_path, 'rb') as f:
                        files = {'file': (filename, f)}
                        response = requests.post(url, headers=headers, files=files)
                    if response.status_code == 200:
                        print(f"✓ Загружено: {filename}")
                    else:
                        print(f"✗ Ошибка загрузки {filename}: {response.status_code}")
                except Exception as e:
                    print(f"✗ Ошибка при загрузке {filename}: {str(e)}")

    def get_confluence_page_content(self, token, page_id):
        url = f"{self.url}/rest/api/content/{page_id}?expand=body.storage"
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        body = resp.json()["body"]["storage"]["value"]
        return body
