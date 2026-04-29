import os
import requests

class GrafanaExporter:
    def __init__(self, url, api_key, dashboard_uid, panels, output_dir, width, height, timeout):
        self.url = url
        self.api_key = api_key
        self.dashboard_uid = dashboard_uid
        self.panels = panels
        self.output_dir = output_dir
        self.width = width
        self.height = height
        self.timeout = timeout

    def check_auth(self):
        url = f"{self.url}/api/health"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                print("✓ Grafana API authorization successful")
                return True
            else:
                print(f"✗ Grafana API authorization failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ Error during Grafana API auth check: {str(e)}")
            return False

    def download_panels(self, start_time, end_time):
        print("Начинаем загрузку графиков из Grafana...")
        os.makedirs(self.output_dir, exist_ok=True)
        headers = {"Authorization": f"Bearer {self.api_key}"}
        for panel_name, panel_id in self.panels:
            try:
                url = f"{self.url}/render/d-solo/{self.dashboard_uid}/"
                params = {
                    'panelId': panel_id,
                    'from': start_time,
                    'to': end_time,
                    'width': self.width,
                    'height': self.height,
                    'timeout': self.timeout,
                    'var-bucket': 'k6',
                    'tz': 'Europe/Moscow'
                }
                response = requests.get(url, headers=headers, params=params, stream=True)
                if response.status_code == 200:
                    filename = f"{self.output_dir}/{panel_name}.png"
                    with open(filename, 'wb') as f:
                        for chunk in response.iter_content(1024):
                            f.write(chunk)
                    print(f"Сохранено: {filename}")
                else:
                    print(f"Ошибка при загрузке {panel_name}: {response.status_code}")
            except Exception as e:
                print(f"Ошибка при загрузке {panel_name}: {str(e)}")
