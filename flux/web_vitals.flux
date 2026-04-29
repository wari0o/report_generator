data = from(bucket: "${bucket}")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => 
    contains(
      value: r._measurement,
      set: [
        "browser_web_vital_cls",
        "browser_web_vital_fcp",
        "browser_web_vital_fid",
        "browser_web_vital_inp",
        "browser_web_vital_lcp",
        "browser_web_vital_ttfb"
      ]
    )
  )
  |> filter(fn: (r) => r._field == "value")
  |> filter(fn: (r) => r.name =~ /docs-/)
  |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)

// Вычисляем статистики отдельно для каждой метрики
mean_stats = data
  |> group(columns: ["_measurement"])
  |> mean()
  |> map(fn: (r) => ({metric: r._measurement, mean: r._value}))

median_stats = data
  |> group(columns: ["_measurement"])
  |> median()
  |> map(fn: (r) => ({metric: r._measurement, median: r._value}))

p90_stats = data
  |> group(columns: ["_measurement"])
  |> toFloat()
  |> quantile(q: 0.9)
  |> map(fn: (r) => ({metric: r._measurement, p90: r._value}))

min_stats = data
  |> group(columns: ["_measurement"])
  |> min()
  |> map(fn: (r) => ({metric: r._measurement, min: r._value}))

max_stats = data
  |> group(columns: ["_measurement"])
  |> max()
  |> map(fn: (r) => ({metric: r._measurement, max: r._value}))

time_stats = data
  |> group(columns: ["_measurement"])
  |> last()
  |> map(fn: (r) => ({metric: r._measurement, _time: r._time}))

// Объединяем статистики последовательно
step1 = join(
  tables: {mean: mean_stats, med: median_stats},
  on: ["metric"]
)

step2 = join(
  tables: {s1: step1, p90: p90_stats},
  on: ["metric"]
)

step3 = join(
  tables: {s2: step2, min: min_stats},
  on: ["metric"]
)

step4 = join(
  tables: {s2: step3, max: max_stats},
  on: ["metric"]
)

final = join(
  tables: {s3: step4, time: time_stats},
  on: ["metric"]
)

// Форматируем результат
final
  |> map(fn: (r) => ({
    "Metrics": r.metric,
    "Average": r.mean,
    "Median": r.median,
    "90%%": r.p90,
    "Min": r.min,
    "Max": r.max,
    "Last update": r._time
  }))
  |> keep(columns: [
    "Metrics",
    "Average",
    "Median",
    "90%%",
    "Min",
    "Max",
  ])
  |> sort(columns: ["Metrics"], desc: true)
  |> yield(name: "metrics_vital_stats")