import json, os
import pandas as pd

CLEAN_FILE    = r"C:\WORK\crime-monitor\data\gdelt_indonesia_crime_clean.parquet"
WEEKLY_FILE   = r"C:\WORK\crime-monitor\dashboard\data\weekly_province.csv"
DISTRICT_FILE = r"C:\WORK\crime-monitor\dashboard\data\district_summary.csv"
MAP_FILE      = r"C:\WORK\crime-monitor\dashboard\data\map_comparison.csv"
OUT_DIR       = r"C:\WORK\crime-monitor\dashboard\data"

PROV_COLORS = ['#e74c3c','#3498db','#2ecc71','#f39c12','#9b59b6','#1abc9c','#e67e22','#34495e']
DIST_COLORS = [
    '#e74c3c','#3498db','#2ecc71','#f39c12','#9b59b6',
    '#1abc9c','#e67e22','#34495e','#e91e63','#00bcd4',
    '#8bc34a','#ff5722','#607d8b','#795548','#9c27b0',
    '#03a9f4','#4caf50','#ff9800','#c0392b','#2980b9',
    '#27ae60','#d35400','#16a085','#8e44ad','#e67e22',
]

def save_json(name, obj):
    path = os.path.join(OUT_DIR, name)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, separators=(',', ':'), ensure_ascii=False)
    print(f"  {name:<42} {os.path.getsize(path)/1024:>7.1f} KB")

def build_datasets(pivot, top_list, all_weeks, colors):
    datasets = []
    for i, name in enumerate(top_list):
        col  = pivot[name] if name in pivot.columns else pd.Series(dtype=float)
        data = [round(float(col.get(w, 0)), 2) for w in all_weeks]
        datasets.append({
            'label':           name,
            'data':            data,
            'borderColor':     colors[i % len(colors)],
            'backgroundColor': 'transparent',
            'borderWidth':     1.5,
            'pointRadius':     0,
            'tension':         0.3,
        })
    return datasets

def calc_trend(curr, prev):
    if prev == 0:
        return 'up' if curr > 0 else 'flat'
    r = curr / prev
    return 'up' if r > 1.15 else ('down' if r < 0.85 else 'flat')

def main():
    print("Loading data sources ...")

    # ── Source files ──────────────────────────────────────────────
    weekly   = pd.read_csv(WEEKLY_FILE,   parse_dates=['week'])
    district = pd.read_csv(DISTRICT_FILE)
    map_cmp  = pd.read_csv(MAP_FILE)

    df = pd.read_parquet(CLEAN_FILE)
    df['date']          = pd.to_datetime(df['SQLDATE'].astype(str), format='%Y%m%d')
    df['intensity']     = df['NumMentions'] * df['GoldsteinScale'].abs()
    df['district_name'] = df['ADM2_EN'].fillna('Unknown')
    df['province_name'] = df['ADM1_EN'].fillna('Unknown')
    df['pcode']         = df['ADM2_PCODE'].fillna('UNKNOWN')
    df['week']          = df['date'].dt.to_period('W-SUN').dt.start_time.dt.strftime('%Y-%m-%d')

    max_date = df['date'].max()

    # ── National weekly ───────────────────────────────────────────
    nat = (
        weekly.groupby('week')
        .agg(intensity=('total_intensity','sum'), events=('event_count','sum'))
        .reset_index().sort_values('week')
    )
    nat['week']      = nat['week'].dt.strftime('%Y-%m-%d')
    nat['rolling4']  = nat['intensity'].rolling(4, min_periods=1).mean().round(2)
    nat['intensity'] = nat['intensity'].round(2)
    all_weeks        = nat['week'].tolist()
    grand_mean       = round(float(nat['intensity'].mean()), 2)

    # ── Province datasets top 8 ───────────────────────────────────
    prov_totals  = weekly.groupby('province_name')['total_intensity'].sum().sort_values(ascending=False)
    top8         = prov_totals.head(8).index.tolist()
    weekly['week_str'] = weekly['week'].dt.strftime('%Y-%m-%d')
    pv_prov = weekly.pivot_table(index='week_str', columns='province_name',
                                  values='total_intensity', fill_value=0)
    prov_datasets = build_datasets(pv_prov, top8, all_weeks, PROV_COLORS)

    # ── Top 25 district bar charts (totals) ───────────────────────
    top25_count  = (
        district.sort_values('event_count', ascending=False).head(25)
        [['district_name','province_name','event_count']].to_dict('records')
    )
    top25_intens = (
        district.sort_values('total_intensity', ascending=False).head(25)
        [['district_name','province_name','total_intensity']].to_dict('records')
    )

    # ── District weekly series ────────────────────────────────────
    dist_wk = (
        df.groupby(['week','district_name'])
        .agg(count=('intensity','count'), intensity=('intensity','sum'))
        .reset_index()
    )
    dist_wk['intensity'] = dist_wk['intensity'].round(2)

    pv_dc = dist_wk.pivot_table(index='week', columns='district_name', values='count',     fill_value=0)
    pv_di = dist_wk.pivot_table(index='week', columns='district_name', values='intensity', fill_value=0)

    top25_dc = dist_wk.groupby('district_name')['count'].sum().sort_values(ascending=False).head(25).index.tolist()
    top25_di = dist_wk.groupby('district_name')['intensity'].sum().sort_values(ascending=False).head(25).index.tolist()

    dist_trend_count  = build_datasets(pv_dc, top25_dc, all_weeks, DIST_COLORS)
    dist_trend_intens = build_datasets(pv_di, top25_di, all_weeks, DIST_COLORS)

    # ── District table ────────────────────────────────────────────
    last7 = (
        df[df['date'] > max_date - pd.Timedelta(days=7)]
        .groupby('pcode')
        .agg(week_events=('intensity','count'), week_intensity=('intensity','sum'))
        .reset_index()
    )
    last7['week_intensity'] = last7['week_intensity'].round(2)

    tbl = (
        district
        .merge(map_cmp[['pcode','curr_intensity','curr_events','prev_intensity','prev_events']],
               on='pcode', how='left')
        .merge(last7, on='pcode', how='left')
        .fillna(0)
    )
    tbl['trend'] = tbl.apply(
        lambda r: calc_trend(float(r['curr_intensity']), float(r['prev_intensity'])), axis=1
    )
    tbl = tbl.sort_values('total_intensity', ascending=False)

    keep = ['district_name','province_name','event_count','total_intensity',
            'curr_events','curr_intensity','prev_events','prev_intensity',
            'week_events','week_intensity','trend']
    dist_table = []
    for row in tbl[keep].to_dict('records'):
        dist_table.append({
            'district_name':  row['district_name'],
            'province_name':  row['province_name'],
            'event_count':    int(row['event_count']),
            'total_intensity':round(float(row['total_intensity']), 1),
            'curr_events':    int(row['curr_events']),
            'curr_intensity': round(float(row['curr_intensity']), 1),
            'prev_events':    int(row['prev_events']),
            'prev_intensity': round(float(row['prev_intensity']), 1),
            'week_events':    int(row['week_events']),
            'week_intensity': round(float(row['week_intensity']), 1),
            'trend':          row['trend'],
        })

    # ── Map lookup ────────────────────────────────────────────────
    map_lookup = {
        str(r['pcode']): {
            'curr':   round(float(r['curr_intensity']),   2),
            'prev':   round(float(r['prev_intensity']),   2),
            'change': round(float(r['intensity_change']), 2),
            'currEv': int(r['curr_events']),
            'prevEv': int(r['prev_events']),
        }
        for _, r in map_cmp.iterrows()
    }

    # ── Meta ──────────────────────────────────────────────────────
    meta = {
        'totalEvents':    int(nat['events'].sum()),
        'totalIntensity': int(nat['intensity'].sum()),
        'grandMean':      grand_mean,
        'weekCount':      len(all_weeks),
        'dateMin':        all_weeks[0],
        'dateMax':        all_weeks[-1],
        'provinceCount':  int((prov_totals > 0).sum()),
        'districtCount':  len(district),
        'mapCurrStart':   (max_date - pd.Timedelta(days=30)).strftime('%d %b %Y'),
        'mapCurrEnd':     max_date.strftime('%d %b %Y'),
        'mapPrevStart':   (max_date - pd.Timedelta(days=60)).strftime('%d %b %Y'),
        'mapPrevEnd':     (max_date - pd.Timedelta(days=30)).strftime('%d %b %Y'),
    }

    # ── National weekly by event code (14x, 18x, 19x) ───────────
    df['event_family'] = df['EventCode'].astype(str).str[:2]
    code_data = {}
    for code in ['14', '18', '19']:
        sub = df[df['event_family'] == code]
        sub_wk = (
            sub.groupby('week')
            .agg(intensity=('intensity','sum'), events=('intensity','count'))
            .reset_index()
        )
        base = pd.DataFrame({'week': all_weeks})
        sub_wk = base.merge(sub_wk, on='week', how='left').fillna(0)
        sub_wk['rolling4_intens'] = sub_wk['intensity'].rolling(4, min_periods=1).mean().round(2)
        sub_wk['rolling4_count']  = sub_wk['events'].rolling(4, min_periods=1).mean().round(2)
        sub_wk['intensity'] = sub_wk['intensity'].round(2)
        sub_wk['events']    = sub_wk['events'].astype(int)
        code_data[code] = sub_wk[['week','events','intensity','rolling4_count','rolling4_intens']].to_dict('records')

    # ── Write ─────────────────────────────────────────────────────
    print("\nWriting JSON files ...")
    save_json('meta.json',                  meta)
    save_json('national.json',              nat[['week','intensity','rolling4']].to_dict('records'))
    save_json('national_by_code.json',      code_data)
    save_json('weeks.json',                 all_weeks)
    save_json('province_datasets.json',     prov_datasets)
    save_json('top25_count.json',           top25_count)
    save_json('top25_intensity.json',       top25_intens)
    save_json('map_lookup.json',            map_lookup)
    save_json('district_trend_count.json',  dist_trend_count)
    save_json('district_trend_intens.json', dist_trend_intens)
    save_json('district_table.json',        dist_table)
    print("\nDone.")

if __name__ == "__main__":
    main()
