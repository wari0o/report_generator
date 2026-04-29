from bs4 import BeautifulSoup

DESIRED_ORDER = ["Average", "Median", "90%%", "Min", "Max"]
reverse_metrics = {"ChangesPer1PacketDU", "Collaborators_Count", "Collaborators_RPS"}

def parse_html_table(table_html):
    """Парсит HTML-таблицу из отчета, возвращает словарь: metric -> [avg, med, p90, min, max] (float или None)"""
    soup = BeautifulSoup(table_html, "html.parser")
    rows = soup.find_all("tr")
    metrics = {}
    for row in rows[1:]:  # пропускаем заголовок
        cells = row.find_all("td")
        if not cells:
            continue
        metric = cells[0].text.strip()
        values = []
        for idx in range(1, 6 + 1):  # 1..6
            try:
                v = float(cells[idx].text.replace(",", "."))
            except (ValueError, IndexError):
                v = None
            values.append(v)    
        metrics[metric] = values
    return metrics

def build_comparison_table(new_metrics, old_metrics):
    """
    Строит HTML сравнительную таблицу с подсветкой.
    new_metrics, old_metrics — словари {metric: [avg, med, p90, min, max]}
    """
    html = ['<table>']
    # Первый заголовочный ряд
    html.append(
        '<tr><th rowspan="2">Metrics</th>'
        + ''.join(f'<th colspan="2">{col}</th>' for col in DESIRED_ORDER)
        + '</tr>'
    )
    # Второй заголовочный ряд
    html.append('<tr>' + '<th>New</th><th>Old</th>'*5 + '</tr>')

    for metric in sorted(set(new_metrics) | set(old_metrics)):
        html.append('<tr>')
        html.append(f'<td>{metric}</td>')
        for i in range(5):
            new = new_metrics.get(metric, [None]*5)[i]
            old = old_metrics.get(metric, [None]*5)[i]
            # Форматируем значения
            new_fmt = f"{new:.2f}" if new is not None else ""
            old_fmt = f"{old:.2f}" if old is not None else ""
            # Подсветка
            style = ""
            if old is not None and new is not None:
                try:
                    n, o = float(new), float(old)
                    if o != 0:
                        delta = (n - o) / o
                        if metric in reverse_metrics:
                            # Инвертированная логика!
                            if delta <= -0.2:
                                style = ' style="background-color:#ffc7ce;"'  # красный если NEW << OLD
                            elif delta >= 0.2:
                                style = ' style="background-color:#c6efce;"'  # зеленый если NEW >> OLD
                        else:
                            # Обычная логика
                            if delta <= -0.2:
                                style = ' style="background-color:#c6efce;"'
                            elif delta >= 0.2:
                                style = ' style="background-color:#ffc7ce;"'
                except Exception:
                    pass
            html.append(f'<td{style}>{new_fmt}</td><td>{old_fmt}</td>')
        html.append('</tr>')
    html.append("</table>")
    return ''.join(html)

def extract_main_tables_from_content(content):
    """Извлекает две первые таблицы отчёта из контента Confluence (сводная и web vitals)"""
    soup = BeautifulSoup(content, "html.parser")
    tables = soup.find_all("table")
    if len(tables) < 2:
        raise Exception("В предыдущем отчёте не найдено двух таблиц для сравнения")
    return tables[0], tables[1]
