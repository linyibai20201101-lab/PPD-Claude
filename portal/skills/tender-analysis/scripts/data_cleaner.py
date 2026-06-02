#!/usr/bin/env python3
"""
data_cleaner.py - 标书数据清洗与去重模块

用法:
    python data_cleaner.py --input <input_file> --output <output_file> [--keyword <product_keyword>]

功能:
    1. 读取原始标书数据（Excel/CSV）
    2. 字段规范化（金额、地址、单位名称）
    3. 项目去重（同一项目多阶段合并）
    4. 输出去重后的清洗数据
"""

import sys
import re
import argparse
import pandas as pd
from pathlib import Path

# ==================== 金额清洗 ====================

def clean_amount(val):
    """将各种格式的金额统一转换为万元数值"""
    if pd.isna(val) or str(val).strip() == '':
        return None
    s = str(val).strip()
    # 提取数字（含小数点）
    num_match = re.search(r'[\d,]+\.?\d*', s.replace(',', ''))
    if not num_match:
        return None
    num = float(num_match.group().replace(',', ''))
    # 单位转换
    if '亿' in s:
        num *= 10000  # 亿元 → 万元
    elif '元' in s and '万' not in s:
        num /= 10000  # 元 → 万元
    # 默认单位为万元
    return round(num, 4)


# ==================== 省份提取 ====================

PROVINCE_ALIASES = {
    '北京': '北京市', '天津': '天津市', '上海': '上海市', '重庆': '重庆市',
    '河北': '河北省', '山西': '山西省', '内蒙古': '内蒙古自治区',
    '辽宁': '辽宁省', '吉林': '吉林省', '黑龙江': '黑龙江省',
    '江苏': '江苏省', '浙江': '浙江省', '安徽': '安徽省', '福建': '福建省',
    '江西': '江西省', '山东': '山东省', '河南': '河南省', '湖北': '湖北省',
    '湖南': '湖南省', '广东': '广东省', '广西': '广西壮族自治区',
    '海南': '海南省', '四川': '四川省', '贵州': '贵州省', '云南': '云南省',
    '西藏': '西藏自治区', '陕西': '陕西省', '甘肃': '甘肃省',
    '青海': '青海省', '宁夏': '宁夏回族自治区', '新疆': '新疆维吾尔自治区',
}

REGION_MAP = {
    '北京市': '华北', '天津市': '华北', '河北省': '华北', '山西省': '华北', '内蒙古自治区': '华北',
    '辽宁省': '东北', '吉林省': '东北', '黑龙江省': '东北',
    '上海市': '华东', '江苏省': '华东', '浙江省': '华东', '安徽省': '华东',
    '福建省': '华东', '江西省': '华东', '山东省': '华东',
    '河南省': '华中', '湖北省': '华中', '湖南省': '华中',
    '广东省': '华南', '广西壮族自治区': '华南', '海南省': '华南',
    '重庆市': '西南', '四川省': '西南', '贵州省': '西南', '云南省': '西南', '西藏自治区': '西南',
    '陕西省': '西北', '甘肃省': '西北', '青海省': '西北', '宁夏回族自治区': '西北', '新疆维吾尔自治区': '西北',
}

def extract_province(address_str):
    """从地址字符串中提取标准省份名称"""
    if pd.isna(address_str):
        return '未知'
    s = str(address_str)
    for alias, standard in PROVINCE_ALIASES.items():
        if alias in s:
            return standard
    return '未知'

def get_region(province):
    return REGION_MAP.get(province, '其他')


# ==================== 状态优先级 ====================

STATUS_PRIORITY = {
    '中标公告': 5, '成交公告': 5, '定标公告': 5,
    '中标结果': 4, '成交结果': 4,
    '招标公告': 3, '采购公告': 3,
    '资格预审': 2, '更正公告': 2,
    '废标公告': 1, '终止公告': 1,
}

def get_status_priority(status_str):
    if pd.isna(status_str):
        return 0
    for keyword, priority in STATUS_PRIORITY.items():
        if keyword in str(status_str):
            return priority
    return 0


# ==================== 主清洗函数 ====================

def clean_and_dedup(df, project_name_col=None, buyer_col=None,
                    status_col=None, amount_col=None, address_col=None,
                    date_col=None):
    """
    执行数据清洗和去重
    
    参数:
        df: 原始 DataFrame
        project_name_col: 项目名称列名
        buyer_col: 采购单位列名
        status_col: 状态列名
        amount_col: 金额列名
        address_col: 地址列名
        date_col: 日期列名
    
    返回:
        cleaned_df: 去重后的 DataFrame
        stats: 清洗统计信息字典
    """
    original_count = len(df)
    df = df.copy()
    
    # 1. 金额清洗
    if amount_col and amount_col in df.columns:
        df['金额_万元'] = df[amount_col].apply(clean_amount)
    
    # 2. 省份提取
    if address_col and address_col in df.columns:
        df['省份'] = df[address_col].apply(extract_province)
        df['大区'] = df['省份'].apply(get_region)
    
    # 3. 状态优先级打分
    if status_col and status_col in df.columns:
        df['_status_priority'] = df[status_col].apply(get_status_priority)
    else:
        df['_status_priority'] = 0
    
    # 4. 日期转换
    if date_col and date_col in df.columns:
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    
    # 5. 去重逻辑
    dedup_key = []
    if project_name_col and project_name_col in df.columns:
        dedup_key.append(project_name_col)
    if buyer_col and buyer_col in df.columns:
        dedup_key.append(buyer_col)
    
    if dedup_key:
        # 同一项目组内，保留状态优先级最高的记录；优先级相同则保留最新
        sort_cols = ['_status_priority']
        sort_asc = [False]
        if date_col and date_col in df.columns:
            sort_cols.append(date_col)
            sort_asc.append(False)
        
        df_sorted = df.sort_values(sort_cols, ascending=sort_asc)
        df_dedup = df_sorted.drop_duplicates(subset=dedup_key, keep='first')
    else:
        df_dedup = df.drop_duplicates()
    
    # 清理辅助列
    if '_status_priority' in df_dedup.columns:
        df_dedup = df_dedup.drop(columns=['_status_priority'])
    
    dedup_count = len(df_dedup)
    stats = {
        'original_count': original_count,
        'dedup_count': dedup_count,
        'removed_count': original_count - dedup_count,
        'dedup_rate': round((original_count - dedup_count) / original_count * 100, 1) if original_count > 0 else 0,
    }
    
    return df_dedup, stats


# ==================== CLI 入口 ====================

def main():
    parser = argparse.ArgumentParser(description='标书数据清洗与去重工具')
    parser.add_argument('--input', required=True, help='输入文件路径（Excel/CSV）')
    parser.add_argument('--output', required=True, help='输出文件路径')
    parser.add_argument('--project-col', default='项目名称', help='项目名称列名')
    parser.add_argument('--buyer-col', default='采购单位', help='采购单位列名')
    parser.add_argument('--status-col', default='公告类型', help='状态列名')
    parser.add_argument('--amount-col', default='金额', help='金额列名')
    parser.add_argument('--address-col', default='地区', help='地址列名')
    parser.add_argument('--date-col', default='发布日期', help='日期列名')
    args = parser.parse_args()
    
    # 读取数据
    input_path = Path(args.input)
    if input_path.suffix.lower() in ['.xlsx', '.xls']:
        df = pd.read_excel(input_path)
    else:
        df = pd.read_csv(input_path, encoding='utf-8-sig')
    
    print(f"读取原始数据: {len(df)} 条")
    print(f"字段列表: {list(df.columns)}")
    
    # 清洗去重
    df_clean, stats = clean_and_dedup(
        df,
        project_name_col=args.project_col,
        buyer_col=args.buyer_col,
        status_col=args.status_col,
        amount_col=args.amount_col,
        address_col=args.address_col,
        date_col=args.date_col,
    )
    
    print(f"\n=== 清洗统计 ===")
    print(f"原始条数: {stats['original_count']}")
    print(f"去重后: {stats['dedup_count']}")
    print(f"去除重复: {stats['removed_count']} 条 (去重率 {stats['dedup_rate']}%)")
    
    # 保存结果
    output_path = Path(args.output)
    if output_path.suffix.lower() in ['.xlsx', '.xls']:
        df_clean.to_excel(output_path, index=False)
    else:
        df_clean.to_csv(output_path, index=False, encoding='utf-8-sig')
    
    print(f"\n已保存至: {output_path}")


if __name__ == '__main__':
    main()
