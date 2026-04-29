GRAFANA_URL = "http://grafana:3000"
GRAFANA_API_KEY = ""
GRAFANA_DASHBOARD_UID = ""
GRAFANA_PANELS = [
    ["Collaborators_count", "panel-13"],
    ["Collaborators_RPS", "panel-14"],
    ["ChangePer1PacketDU", "panel-12"],
    ["DU_Responce_time", "panel-4"],
    ["cINP_Responce_time", "panel-10"]
]
OUTPUT_DIR = "grafana_screenshots"
WIDTH = 1000
HEIGHT = 500
TIMEOUT = 60
CONFLUENCE_URL = ""
CONFLUENCE_SPACE_KEY = ""
INFLUXDB_URL = "http://influxdb:8086"
INFLUXDB_TOKEN = ""
INFLUXDB_ORG = "myorg"
INFLUXDB_BUCKET = "k6"
FLUX_QUERIES_FOLDER = "flux"