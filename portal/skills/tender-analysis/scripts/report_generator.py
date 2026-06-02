#!/usr/bin/env python3
"""
report_generator.py - 生成交互式HTML标书分析报告

用法:
    python report_generator.py --input <cleaned_excel> --output <report.html> [--keyword <产品名称>]

生成包含15项分析图表的ECharts交互式报告
"""

import sys
import json
import argparse
import pandas as pd
from pathlib import Path
from datetime import datetime

# 导入分析模块（同目录）
sys.path.insert(0, str(Path(__file__).parent))
from data_cleaner import clean_and_dedup, extract_province, get_region
from info_extractor import enrich_dataframe


def load_and_prepare(input_path, col_mapping, keyword=None):
    """加载并预处理数据"""
    p = Path(input_path)
    if p.suffix.lower() in ['.xlsx', '.xls']:
        df = pd.read_excel(p)
    else:
        df = pd.read_csv(p, encoding='utf-8-sig')
    
    # 字段映射重命名
    rename_map = {v: k for k, v in col_mapping.items() if v and v in df.columns}
    df = df.rename(columns=rename_map)
    
    # 清洗去重
    df, stats = clean_and_dedup(
        df,
        project_name_col='项目名称' if '项目名称' in df.columns else None,
        buyer_col='采购单位' if '采购单位' in df.columns else None,
        status_col='状态' if '状态' in df.columns else None,
        amount_col='金额' if '金额' in df.columns else None,
        address_col='地区' if '地区' in df.columns else None,
        date_col='日期' if '日期' in df.columns else None,
    )
    
    # 信息提炼
    df = enrich_dataframe(df, keyword=keyword)
    
    return df, stats


def compute_charts(df):
    """计算所有图表所需的数据"""
    charts = {}
    
    # 1. 年度项目数量趋势
    if '日期' in df.columns:
        df['年份'] = pd.to_datetime(df['日期'], errors='coerce').dt.year
        year_trend = df.groupby('年份').size().reset_index(name='数量')
        year_trend = year_trend.dropna(subset=['年份'])
        charts['year_trend'] = {
            'years': year_trend['年份'].astype(int).tolist(),
            'counts': year_trend['数量'].tolist(),
        }
    
    # 2. 机构类型分布
    if '机构类型' in df.columns:
        org_dist = df['机构类型'].value_counts()
        charts['org_type'] = {
            'data': [{'name': k, 'value': int(v)} for k, v in org_dist.items()]
        }
    
    # 3. 省份分布（Top15）
    if '省份' in df.columns:
        prov_dist = df[df['省份'] != '未知']['省份'].value_counts().head(15)
        charts['province'] = {
            'provinces': prov_dist.index.tolist(),
            'counts': prov_dist.values.tolist(),
        }
    
    # 4. 大区趋势（折线图）
    if '大区' in df.columns and '年份' in df.columns:
        region_year = df.groupby(['大区', '年份']).size().unstack(fill_value=0)
        charts['region_trend'] = {
            'years': [int(y) for y in region_year.columns.tolist()],
            'series': [
                {'name': region, 'data': region_year.loc[region].tolist()}
                for region in region_year.index
            ]
        }
    
    # 5. 总金额统计
    if '金额_万元' in df.columns:
        amounts = df['金额_万元'].dropna()
        charts['amount_stats'] = {
            'total': round(float(amounts.sum()), 2),
            'mean': round(float(amounts.mean()), 2),
            'median': round(float(amounts.median()), 2),
            'max': round(float(amounts.max()), 2),
            'min': round(float(amounts.min()), 2),
            'count': int(amounts.count()),
        }
    
    # 6. 价格区间分布
    if '金额_万元' in df.columns:
        bins = [0, 5, 20, 50, 100, 500, float('inf')]
        labels = ['<5万', '5-20万', '20-50万', '50-100万', '100-500万', '>500万']
        df['价格区间'] = pd.cut(df['金额_万元'], bins=bins, labels=labels)
        price_dist = df['价格区间'].value_counts().reindex(labels, fill_value=0)
        charts['price_range'] = {
            'ranges': labels,
            'counts': price_dist.values.tolist(),
        }
    
    # 7. 行业 × 价格区间
    if '行业名称' in df.columns and '价格区间' in df.columns:
        ind_price = df.groupby(['行业名称', '价格区间']).size().unstack(fill_value=0)
        charts['industry_price'] = {
            'industries': ind_price.index.tolist(),
            'ranges': [str(c) for c in ind_price.columns.tolist()],
            'data': ind_price.values.tolist(),
        }
    
    # 8. 厂商中标数量排名（Top10）
    if '厂商名称' in df.columns:
        vendor_rank = df[df['厂商名称'] != '未知']['厂商名称'].value_counts().head(10)
        charts['vendor_rank'] = {
            'vendors': vendor_rank.index.tolist(),
            'counts': vendor_rank.values.tolist(),
        }
    
    # 9. 厂商 × 区域分布（热力矩阵）
    if '厂商名称' in df.columns and '大区' in df.columns:
        top_vendors = df[df['厂商名称'] != '未知']['厂商名称'].value_counts().head(8).index
        df_top = df[df['厂商名称'].isin(top_vendors)]
        v_r = df_top.groupby(['厂商名称', '大区']).size().unstack(fill_value=0)
        charts['vendor_region'] = {
            'vendors': v_r.index.tolist(),
            'regions': v_r.columns.tolist(),
            'data': [[int(v_r.iloc[i, j]) for j in range(len(v_r.columns))]
                     for i in range(len(v_r))],
        }
    
    # 10. 厂商平均价格对比
    if '厂商名称' in df.columns and '金额_万元' in df.columns:
        top_vendors = df[df['厂商名称'] != '未知']['厂商名称'].value_counts().head(8).index
        vendor_price = (df[df['厂商名称'].isin(top_vendors)]
                        .groupby('厂商名称')['金额_万元']
                        .mean()
                        .round(2)
                        .sort_values(ascending=False))
        charts['vendor_price'] = {
            'vendors': vendor_price.index.tolist(),
            'avg_prices': vendor_price.values.tolist(),
        }
    
    return charts


def generate_html(df, charts, stats, keyword='产品', output_path='report.html'):
    """生成完整的HTML报告"""
    
    kpi_total = stats['dedup_count']
    kpi_amount = charts.get('amount_stats', {}).get('total', 0)
    kpi_provinces = len(df['省份'].unique()) if '省份' in df.columns else 0
    kpi_vendors = df[df['厂商名称'] != '未知']['厂商名称'].nunique() if '厂商名称' in df.columns else 0
    
    charts_json = json.dumps(charts, ensure_ascii=False)
    
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{keyword} - 标书分析报告</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; background: #f0f2f5; color: #333; }}
  .header {{ background: linear-gradient(135deg, #1a237e, #1565c0); color: white; padding: 24px 32px; }}
  .header h1 {{ font-size: 24px; font-weight: 600; }}
  .header p {{ font-size: 13px; opacity: 0.8; margin-top: 6px; }}
  .kpi-row {{ display: flex; gap: 16px; padding: 20px 24px; flex-wrap: wrap; }}
  .kpi-card {{ flex: 1; min-width: 180px; background: white; border-radius: 8px;
               padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,.08); text-align: center; }}
  .kpi-card .value {{ font-size: 32px; font-weight: 700; color: #1565c0; }}
  .kpi-card .label {{ font-size: 13px; color: #666; margin-top: 4px; }}
  .section {{ padding: 0 24px 24px; }}
  .section-title {{ font-size: 16px; font-weight: 600; color: #1a237e;
                    border-left: 4px solid #1565c0; padding-left: 12px; margin: 20px 0 12px; }}
  .chart-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(480px, 1fr)); gap: 16px; }}
  .chart-card {{ background: white; border-radius: 8px; padding: 16px;
                 box-shadow: 0 2px 8px rgba(0,0,0,.08); }}
  .chart-card h3 {{ font-size: 14px; color: #444; margin-bottom: 12px; }}
  .chart-box {{ width: 100%; height: 300px; }}
  .footer {{ text-align: center; padding: 16px; color: #999; font-size: 12px; }}
</style>
</head>
<body>
<div class="header">
  <h1>📊 {keyword} 标书分析报告</h1>
  <p>生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')} | 原始数据 {stats['original_count']} 条 → 去重后 {stats['dedup_count']} 条（去重率 {stats['dedup_rate']}%）</p>
</div>

<div class="kpi-row">
  <div class="kpi-card"><div class="value">{kpi_total}</div><div class="label">项目总数</div></div>
  <div class="kpi-card"><div class="value">{kpi_amount:,.0f} 万</div><div class="label">项目总金额</div></div>
  <div class="kpi-card"><div class="value">{kpi_provinces}</div><div class="label">覆盖省份</div></div>
  <div class="kpi-card"><div class="value">{kpi_vendors}</div><div class="label">参与厂商</div></div>
</div>

<div class="section">
  <div class="section-title">基础分析</div>
  <div class="chart-grid">
    <div class="chart-card"><h3>年度项目数量趋势</h3><div class="chart-box" id="chart_year"></div></div>
    <div class="chart-card"><h3>采购单位类型分布</h3><div class="chart-box" id="chart_org"></div></div>
  </div>
</div>

<div class="section">
  <div class="section-title">区域分析</div>
  <div class="chart-grid">
    <div class="chart-card"><h3>省份项目数量 Top15</h3><div class="chart-box" id="chart_province"></div></div>
    <div class="chart-card"><h3>大区项目趋势</h3><div class="chart-box" id="chart_region_trend"></div></div>
  </div>
</div>

<div class="section">
  <div class="section-title">金额分析</div>
  <div class="chart-grid">
    <div class="chart-card"><h3>价格区间分布</h3><div class="chart-box" id="chart_price_range"></div></div>
    <div class="chart-card"><h3>行业 × 价格区间（项目数）</h3><div class="chart-box" id="chart_ind_price"></div></div>
  </div>
</div>

<div class="section">
  <div class="section-title">竞争格局分析</div>
  <div class="chart-grid">
    <div class="chart-card"><h3>厂商中标数量排名 Top10</h3><div class="chart-box" id="chart_vendor_rank"></div></div>
    <div class="chart-card"><h3>厂商平均中标价格对比（万元）</h3><div class="chart-box" id="chart_vendor_price"></div></div>
    <div class="chart-card" style="grid-column: 1/-1;"><h3>厂商 × 区域中标分布热力图</h3><div class="chart-box" id="chart_vendor_region" style="height:360px;"></div></div>
  </div>
</div>

<div class="footer">本报告由 WorkBuddy 标书分析技能自动生成</div>

<script>
const D = {charts_json};

function initChart(id, option) {{
  const el = document.getElementById(id);
  if (!el) return;
  const chart = echarts.init(el);
  chart.setOption(option);
  window.addEventListener('resize', () => chart.resize());
}}

// 年度趋势
if (D.year_trend) {{
  initChart('chart_year', {{
    tooltip: {{ trigger: 'axis' }},
    xAxis: {{ type: 'category', data: D.year_trend.years }},
    yAxis: {{ type: 'value', name: '项目数' }},
    series: [{{ type: 'bar', data: D.year_trend.counts, itemStyle: {{ color: '#1565c0' }},
               label: {{ show: true, position: 'top' }} }}]
  }});
}}

// 机构类型
if (D.org_type) {{
  initChart('chart_org', {{
    tooltip: {{ trigger: 'item', formatter: '{{b}}: {{c}} ({{d}}%)' }},
    legend: {{ bottom: 0 }},
    series: [{{ type: 'pie', radius: ['40%', '70%'], data: D.org_type.data,
               label: {{ formatter: '{{b}}\\n{{d}}%' }} }}]
  }});
}}

// 省份分布
if (D.province) {{
  initChart('chart_province', {{
    tooltip: {{ trigger: 'axis' }},
    xAxis: {{ type: 'value', name: '项目数' }},
    yAxis: {{ type: 'category', data: D.province.provinces.reverse(), axisLabel: {{ fontSize: 11 }} }},
    series: [{{ type: 'bar', data: D.province.counts.reverse(),
               itemStyle: {{ color: '#26a69a' }}, label: {{ show: true, position: 'right' }} }}]
  }});
}}

// 大区趋势
if (D.region_trend) {{
  initChart('chart_region_trend', {{
    tooltip: {{ trigger: 'axis' }},
    legend: {{ bottom: 0 }},
    xAxis: {{ type: 'category', data: D.region_trend.years }},
    yAxis: {{ type: 'value', name: '项目数' }},
    series: D.region_trend.series.map(s => ({{ ...s, type: 'line', smooth: true }}))
  }});
}}

// 价格区间
if (D.price_range) {{
  initChart('chart_price_range', {{
    tooltip: {{ trigger: 'axis' }},
    xAxis: {{ type: 'category', data: D.price_range.ranges }},
    yAxis: {{ type: 'value', name: '项目数' }},
    series: [{{ type: 'bar', data: D.price_range.counts,
               itemStyle: {{ color: '#ef6c00' }}, label: {{ show: true, position: 'top' }} }}]
  }});
}}

// 行业×价格区间
if (D.industry_price) {{
  const ipSeries = D.industry_price.ranges.map((r, ri) => ({{
    name: r, type: 'bar', stack: 'total',
    data: D.industry_price.data.map(row => row[ri] || 0)
  }}));
  initChart('chart_ind_price', {{
    tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'shadow' }} }},
    legend: {{ bottom: 0, type: 'scroll' }},
    xAxis: {{ type: 'category', data: D.industry_price.industries, axisLabel: {{ interval: 0, rotate: 30, fontSize: 10 }} }},
    yAxis: {{ type: 'value' }},
    series: ipSeries
  }});
}}

// 厂商排名
if (D.vendor_rank) {{
  initChart('chart_vendor_rank', {{
    tooltip: {{ trigger: 'axis' }},
    xAxis: {{ type: 'value', name: '中标数' }},
    yAxis: {{ type: 'category', data: D.vendor_rank.vendors.reverse(), axisLabel: {{ fontSize: 11 }} }},
    series: [{{ type: 'bar', data: D.vendor_rank.counts.reverse(),
               itemStyle: {{ color: '#7b1fa2' }}, label: {{ show: true, position: 'right' }} }}]
  }});
}}

// 厂商价格
if (D.vendor_price) {{
  initChart('chart_vendor_price', {{
    tooltip: {{ trigger: 'axis' }},
    xAxis: {{ type: 'category', data: D.vendor_price.vendors, axisLabel: {{ interval: 0, rotate: 30, fontSize: 10 }} }},
    yAxis: {{ type: 'value', name: '万元' }},
    series: [{{ type: 'bar', data: D.vendor_price.avg_prices,
               itemStyle: {{ color: '#c62828' }}, label: {{ show: true, position: 'top',
               formatter: v => v.value.toFixed(0) + '万' }} }}]
  }});
}}

// 厂商×区域热力矩阵
if (D.vendor_region) {{
  const vrData = [];
  D.vendor_region.data.forEach((row, vi) => row.forEach((val, ri) => vrData.push([ri, vi, val])));
  const maxVal = Math.max(...vrData.map(d => d[2]));
  initChart('chart_vendor_region', {{
    tooltip: {{ formatter: p => `${{D.vendor_region.vendors[p.data[1]]}} / ${{D.vendor_region.regions[p.data[0]]}}: ${{p.data[2]}} 项` }},
    xAxis: {{ type: 'category', data: D.vendor_region.regions }},
    yAxis: {{ type: 'category', data: D.vendor_region.vendors }},
    visualMap: {{ min: 0, max: maxVal, calculable: true, orient: 'horizontal', bottom: 0,
                  inRange: {{ color: ['#fff', '#1565c0'] }} }},
    series: [{{ type: 'heatmap', data: vrData, label: {{ show: true }} }}]
  }});
}}
</script>
</body>
</html>"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"✅ 报告已生成: {output_path}")


def main():
    parser = argparse.ArgumentParser(description='生成标书分析HTML报告')
    parser.add_argument('--input', required=True, help='输入文件（Excel/CSV）')
    parser.add_argument('--output', default='tender_report.html', help='输出HTML路径')
    parser.add_argument('--keyword', default='产品', help='检索关键词（用于报告标题）')
    parser.add_argument('--project-col', default='项目名称')
    parser.add_argument('--buyer-col', default='采购单位')
    parser.add_argument('--vendor-col', default='中标单位')
    parser.add_argument('--amount-col', default='金额')
    parser.add_argument('--address-col', default='地区')
    parser.add_argument('--status-col', default='公告类型')
    parser.add_argument('--date-col', default='发布日期')
    args = parser.parse_args()
    
    col_mapping = {
        '项目名称': args.project_col, '采购单位': args.buyer_col,
        '中标单位': args.vendor_col, '金额': args.amount_col,
        '地区': args.address_col, '状态': args.status_col, '日期': args.date_col,
    }
    
    print(f"📂 加载数据: {args.input}")
    df, stats = load_and_prepare(args.input, col_mapping, keyword=args.keyword)
    print(f"✅ 去重完成: {stats}")
    
    print("📊 计算分析图表数据...")
    charts = compute_charts(df)
    
    print("🎨 生成HTML报告...")
    generate_html(df, charts, stats, keyword=args.keyword, output_path=args.output)


if __name__ == '__main__':
    main()
