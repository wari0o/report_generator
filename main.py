import argparse
import config
from grafana_exporter import GrafanaExporter
from influxdb_exporter import InfluxDBExporter
from confluence_publisher import ConfluencePublisher
from compare import parse_html_table, build_comparison_table, extract_main_tables_from_content
import sys

def main():
    parser = argparse.ArgumentParser(description='Grafana to Confluence exporter')
    parser.add_argument('--start-time', required=True, help='Start time в формате YYYY-MM-DDTHH:MM:SS.000Z или timestamp')
    parser.add_argument('--end-time', required=True, help='End time в формате YYYY-MM-DDTHH:MM:SS.000Z или timestamp')
    parser.add_argument('--confluence-pat', required=True, help='Confluence Personal Access Token')
    parser.add_argument('--confluence-parent-id', required=True, help='Parent page ID в Confluence')
    parser.add_argument('--confluence-page-name', required=True, help='Имя создаваемой страницы')
    parser.add_argument('--compare', choices=['true', 'false'], default='false', required=False, help='Включить режим сравнения с предыдущим отчетом: "true" или "false"')
    parser.add_argument('--compare-page-id', required=False, help='ID страницы предыдущего отчета для сравнения')
    args = parser.parse_args()

    # Экспорт из InfluxDB
    influx = InfluxDBExporter(
        config.INFLUXDB_URL,
        config.INFLUXDB_TOKEN,
        config.INFLUXDB_ORG,
        config.INFLUXDB_BUCKET,
        config.FLUX_QUERIES_FOLDER
    )
    metrics_table_html = influx.get_metrics_stats_table_html(args.start_time, args.end_time)
    webvitals_table_html = influx.get_web_vitals_table_html(args.start_time, args.end_time)

    metrics_comparison_spoiler = ''
    webvitals_comparison_spoiler = ''

    # Сравнение текущего теста с другим
    confluence = ConfluencePublisher(
    config.CONFLUENCE_URL,
    config.CONFLUENCE_SPACE_KEY,
    config.OUTPUT_DIR
    )

    if getattr(args, 'compare', False) and getattr(args, 'compare_page_id', None):
        # 1. Получаем старую страницу из Confluence
        print(f"[Сравнение] Загрузка предыдущей страницы отчета (compare_page_id == {args.compare_page_id}) из Confluence...")
        old_content = confluence.get_confluence_page_content(args.confluence_pat, args.compare_page_id)

        # 2. Извлекаем таблицы
        print("[Сравнение] Извлечение таблиц из содержания страницы...")
        old_metrics_html, old_webvitals_html = extract_main_tables_from_content(old_content)

        # 3. Парсим таблицы
        print("[Сравнение] Парсинг таблиц предыдущего и текущего отчета...")
        old_metrics = parse_html_table(str(old_metrics_html))
        old_webvitals = parse_html_table(str(old_webvitals_html))
        new_metrics = parse_html_table(metrics_table_html)
        new_webvitals = parse_html_table(webvitals_table_html)

        # 4. Сравниваем
        print("[Сравнение] Генерация сравнительных таблиц...")
        metrics_comparison_table = build_comparison_table(new_metrics, old_metrics)
        webvitals_comparison_table = build_comparison_table(new_webvitals, old_webvitals)

        # 5. Собираем html-блоки сравнения
        print("[Сравнение] Формирование блоков для итогового отчета...")
        metrics_comparison_spoiler = f"""
        <ac:structured-macro ac:name="expand">
        <ac:parameter ac:name="title">Сводная таблица (сравнение)</ac:parameter>
        <ac:rich-text-body>
            <p>Сравнение с <a href="{config.CONFLUENCE_URL}/pages/viewpage.action?pageId={args.compare_page_id}">
            этой страницей</a>.</p>
            {metrics_comparison_table}
        </ac:rich-text-body>
        </ac:structured-macro>
        """

        webvitals_comparison_spoiler = f"""
        <ac:structured-macro ac:name="expand">
        <ac:parameter ac:name="title">K6 Browser Web Vitals (сравнение)</ac:parameter>
        <ac:rich-text-body>
            <p>Сравнение с <a href="{config.CONFLUENCE_URL}/pages/viewpage.action?pageId={args.compare_page_id}">
            этой страницей</a>.</p>
            {webvitals_comparison_table}
        </ac:rich-text-body>
        </ac:structured-macro>
        """
        print("[Сравнение] Блоки сравнения готовы для вставки в отчет.")
    else:
        print(f"[Сравнение] Сравнение не требуется (compare == {args.compare}).")

    # Экспорт Grafana
    grafana = GrafanaExporter(
        config.GRAFANA_URL,
        config.GRAFANA_API_KEY,
        config.GRAFANA_DASHBOARD_UID,
        config.GRAFANA_PANELS,
        config.OUTPUT_DIR,
        config.WIDTH,
        config.HEIGHT,
        config.TIMEOUT
    )
    # Проверка авторизации Grafana перед основной работой
    if not grafana.check_auth():
        print("Ошибка авторизации в Grafana. Проверьте API-ключ и URL.")
        exit(1)

    grafana.download_panels(args.start_time, args.end_time)

    # Формируем content для страницы Confluence
    with open("content_template.html", "r", encoding="utf-8") as f:
        content_template = f.read()

    content = content_template.format(
        metrics_table=metrics_table_html,
        webvitals_table=webvitals_table_html,
        metrics_comparison_spoiler=metrics_comparison_spoiler,
        webvitals_comparison_spoiler=webvitals_comparison_spoiler
    )

    # Публикация в Confluence
    if not confluence.check_auth(args.confluence_pat):
        print("Проверьте следующее:")
        print("1. Актуальность PAT (срок действия)")
        print("2. Права доступа PAT (нужны write:content)")
        print("3. URL Confluence (должен заканчиваться без /)")
        exit(1)

    # page_id = confluence.create_page(args.confluence_pat, args.confluence_parent_id, args.confluence_page_name)
    page_id = confluence.create_page(
        token=args.confluence_pat,
        parent_id=args.confluence_parent_id,
        page_name=args.confluence_page_name,
        content=content
    )
    if page_id:
        confluence.upload_attachments(page_id, args.confluence_pat)

    print("\nПроцесс завершен!")


if __name__ == "__main__":
    main()