from nicegui import ui
import json
from pathlib import Path
from datetime import datetime, date, timedelta
from collections import defaultdict

DATA_FILE = Path("snore_data.json")

LEVEL_LABELS = {1: "軽い", 2: "やや強い", 3: "普通", 4: "強い", 5: "激しい"}


def load_data():
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text())
    return []


def save_data(data):
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def compute_stats(records):
    if not records:
        return {"total": 0, "avg_level": "-", "max_streak": 0, "worst_day": "-"}

    levels = [r["level"] for r in records]
    avg_level = round(sum(levels) / len(levels), 1)

    day_map = {0: "月", 1: "火", 2: "水", 3: "木", 4: "金", 5: "土", 6: "日"}
    day_counts = defaultdict(int)
    for r in records:
        d = datetime.strptime(r["date"], "%Y-%m-%d")
        day_counts[day_map[d.weekday()]] += 1
    worst_day = (max(day_counts, key=day_counts.get) + "曜日") if day_counts else "-"

    sorted_dates = sorted(set(r["date"] for r in records))
    max_streak = cur = 1
    for i in range(1, len(sorted_dates)):
        d1 = datetime.strptime(sorted_dates[i - 1], "%Y-%m-%d").date()
        d2 = datetime.strptime(sorted_dates[i], "%Y-%m-%d").date()
        cur = cur + 1 if (d2 - d1).days == 1 else 1
        max_streak = max(max_streak, cur)

    return {
        "total": len(records),
        "avg_level": avg_level,
        "max_streak": max_streak,
        "worst_day": worst_day,
    }


def get_chart_data(records, days=30):
    end = date.today()
    start = end - timedelta(days=days - 1)

    date_level = {}
    for r in records:
        d = r["date"]
        if d not in date_level or r["level"] > date_level[d]:
            date_level[d] = r["level"]

    categories, data = [], []
    for i in range(days):
        d = start + timedelta(days=i)
        d_str = d.strftime("%Y-%m-%d")
        categories.append(f"{d.month}/{d.day}")
        data.append(date_level.get(d_str, 0))

    return categories, data


@ui.page("/")
def index():
    records = load_data()
    stats = compute_stats(records)
    categories, chart_data = get_chart_data(records)

    ui.add_head_html("<style>body { background: #f8fafc; }</style>")

    with ui.column().classes("w-full max-w-5xl mx-auto p-6 gap-6"):
        with ui.row().classes("items-center gap-3"):
            ui.label("いびき記録ダッシュボード").classes("text-3xl font-bold text-slate-700")

        with ui.row().classes("w-full gap-4"):
            for label, value, card_cls in [
                ("総記録数", f"{stats['total']}日", "bg-indigo-50 border-indigo-200 text-indigo-700"),
                ("平均レベル", str(stats["avg_level"]), "bg-blue-50 border-blue-200 text-blue-700"),
                ("最長連続記録", f"{stats['max_streak']}日", "bg-orange-50 border-orange-200 text-orange-700"),
                ("多いいびき曜日", stats["worst_day"], "bg-purple-50 border-purple-200 text-purple-700"),
            ]:
                with ui.card().classes(f"flex-1 p-4 text-center border {card_cls}"):
                    ui.label(value).classes("text-2xl font-bold")
                    ui.label(label).classes("text-sm text-gray-500 mt-1")

        ui.echart({
            "title": {"text": "過去30日間のいびきレベル", "textStyle": {"fontSize": 14, "color": "#475569"}},
            "tooltip": {"trigger": "axis", "formatter": "{b}: レベル {c}"},
            "xAxis": {
                "type": "time",
                "data": categories,
                "axisLabel": {"rotate": 45, "fontSize": 10},
            },
            "yAxis": {
                "type": "value",
                "min": 0,
                "max": 5,
                "interval": 1,
                "axisLabel": {"formatter": "Lv.{value}"},
            },
            "series": [{
                "name": "いびきレベル",
                "data": chart_data,
                "type": "line",
                "itemStyle": {
                    "color": {
                        "type": "linear",
                        "x": 0, "y": 0, "x2": 0, "y2": 1,
                        "colorStops": [
                            {"offset": 0, "color": "#818cf8"},
                            {"offset": 1, "color": "#6366f1"},
                        ],
                    }
                },
            }],
            "grid": {"bottom": "22%", "top": "15%"},
        }).classes("w-full h-64")

        with ui.card().classes("w-full p-6"):
            ui.label("新しい記録を追加").classes("text-lg font-semibold text-slate-700 mb-4")
            with ui.row().classes("w-full gap-4 flex-wrap items-end"):
                date_input = ui.input("日付", value=date.today().strftime("%Y-%m-%d")).classes("flex-1 min-w-36")
                level_input = ui.number("いびきレベル (1-5)", value=3, min=1, max=5, step=1).classes("flex-1 min-w-36")
                duration_input = ui.number("時間 (分)", value=0, min=0).classes("flex-1 min-w-36")
                memo_input = ui.input("メモ (任意)").classes("flex-1 min-w-48")

            def add_record():
                if not date_input.value:
                    ui.notify("日付を入力してください", type="warning")
                    return
                new_record = {
                    "date": date_input.value,
                    "level": int(level_input.value or 3),
                    "duration_min": int(duration_input.value or 0),
                    "memo": memo_input.value or "",
                }
                data = load_data()
                data.append(new_record)
                data.sort(key=lambda x: x["date"], reverse=True)
                save_data(data)
                ui.notify("記録を保存しました", type="positive")
                ui.navigate.reload()

            ui.button("記録する", on_click=add_record).classes("bg-indigo-500 text-white px-6 mt-2")

        with ui.card().classes("w-full p-6"):
            ui.label("記録一覧 (直近20件)").classes("text-lg font-semibold text-slate-700 mb-4")

            columns = [
                {"name": "date", "label": "日付", "field": "date", "align": "left"},
                {"name": "level_label", "label": "レベル", "field": "level_label", "align": "center"},
                {"name": "duration_min", "label": "時間(分)", "field": "duration_min", "align": "center"},
                {"name": "memo", "label": "メモ", "field": "memo", "align": "left"},
            ]
            recent = sorted(records, key=lambda x: x["date"], reverse=True)[:20]
            rows = [
                {**r, "level_label": f"Lv.{r['level']} {LEVEL_LABELS.get(r['level'], '')}"}
                for r in recent
            ]

            if rows:
                ui.table(columns=columns, rows=rows, row_key="date").classes("w-full")
            else:
                ui.label("まだ記録がありません。上のフォームから追加してください。").classes(
                    "text-gray-400 text-center py-8 w-full"
                )


ui.run(title="いびきダッシュボード", port=8080, reload=False)
