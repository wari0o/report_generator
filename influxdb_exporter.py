import requests
import os
import csv
import io
from datetime import datetime, timezone

class InfluxDBExporter:
    DESIRED_ORDER = ["Metrics", "Average", "Median", "90%%", "Min", "Max"]

    def __init__(self, url, token, org, bucket, flux_folder):
        self.url = url.rstrip("/")
        self.token = token
        self.org = org
        self.bucket = bucket
        self.flux_folder = flux_folder

    def _ms_to_iso(self, t):
        """Преобразует миллисекунды от эпохи в ISO8601, если необходимо."""
        if isinstance(t, (int, float)) or (isinstance(t, str) and t.isdigit()):
            dt = datetime.fromtimestamp(int(t)/1000, tz=timezone.utc)
            return dt.isoformat(timespec='milliseconds').replace("+00:00", "Z")
        return t  # если уже ISO8601

    def _read_query(self, query_filename):
        query_path = os.path.join(self.flux_folder, query_filename)
        print(f"Загрузка flux-запроса из {query_path} ...")
        with open(query_path, "r", encoding="utf-8") as f:
            content = f.read()
        print("Шаблон flux-запроса успешно загружен.")
        return content

    def _get_table(self, start_time, end_time, query_filename, windowPeriod="1m"):
        print(f"Начало запроса к InfluxDB: {query_filename}")
        start_iso = self._ms_to_iso(start_time)
        end_iso = self._ms_to_iso(end_time)
        print(f"Интервал времени: {start_iso} — {end_iso}")

        query = self._read_query(query_filename)
        query = query.replace("${bucket}", self.bucket)
        query = query.replace("v.timeRangeStart", start_iso)
        query = query.replace("v.timeRangeStop", end_iso)
        query = query.replace("v.windowPeriod", windowPeriod)

        # print("Готовый flux-запрос:")
        # print(query)

        headers = {
            "Authorization": f"Token {self.token}",
            "Content-Type": "application/vnd.flux",
            "Accept": "application/csv"
        }
        params = {"org": self.org}
        print("Выполнение HTTP-запроса к InfluxDB ...")
        resp = requests.post(
            f"{self.url}/api/v2/query",
            params=params,
            headers=headers,
            data=query.encode("utf-8")
        )
        if resp.status_code != 200:
            print("ОШИБКА ВЫПОЛНЕНИЯ Flux-запроса!")
            print("ACTUAL FLUX QUERY:", query)
            raise Exception(f"InfluxDB error {resp.status_code}: {resp.text}")
        else:
            print("Ответ от InfluxDB успешно получен.")
        csv_reader = csv.reader(io.StringIO(resp.text))
        rows = [row for row in csv_reader if row and not row[0].startswith('#')]
        if not rows:
            print("ACTUAL FLUX QUERY:", query)
            raise Exception("No valid data returned from InfluxDB")
        header = rows[0]
        data_rows = rows[1:]
        print(f"Результат: {len(data_rows)} строк данных получено.")
        return header, data_rows

    def table_html(self, header, rows):
        indices = []
        for col in self.DESIRED_ORDER:
            try:
                indices.append(header.index(col))
            except ValueError:
                raise Exception(f"Ожидаемого столбца '{col}' нет в данных из InfluxDB!")
        float_cols = {"Average", "Median", "90%%", "Min", "Max"}

        html = ['<table>']
        html.append('<tr>' + ''.join(f'<th>{col}</th>' for col in self.DESIRED_ORDER) + '</tr>')
        for row in rows:
            html.append('<tr>')
            for idx, col in zip(indices, self.DESIRED_ORDER):
                val = row[idx]
                if col in float_cols:
                    try:
                        val = f"{float(val):.2f}"
                    except (ValueError, TypeError):
                        pass
                html.append(f'<td>{val}</td>')
            html.append('</tr>')
        html.append('</table>')
        return ''.join(html)

    def get_metrics_stats_table_html(self, start_time, end_time):
        print("=== Экспорт статистики метрик InfluxDB для отчёта ===")
        header, rows = self._get_table(start_time, end_time, "metrics_stats.flux")
        print("HTML-таблица для Metrics готова.\n")
        return self.table_html(header, rows)

    def get_web_vitals_table_html(self, start_time, end_time):
        print("=== Экспорт K6 Browser WebVitals из InfluxDB для отчёта ===")
        header, rows = self._get_table(start_time, end_time, "web_vitals.flux")
        print("HTML-таблица для WebVitals готова.\n")
        return self.table_html(header, rows)
