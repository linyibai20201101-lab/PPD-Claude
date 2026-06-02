#!/usr/bin/env python3
"""
info_extractor.py - 标书维度信息提炼模块

功能：
    - 从项目名称/采购单位/产品详情中提炼6个核心维度
    - 行业识别、机构类型判断、产品参数提取
"""

import re
import pandas as pd


# ==================== 行业关键词 ====================

INDUSTRY_KEYWORDS = {
    'SEMI': ['半导体', '集成电路', '芯片', '晶圆', '封装测试', '光刻', '蚀刻', '工艺检测', '制程', 'EUV', 'CVD', 'PVD'],
    'OPT':  ['光学', '显微镜', '光谱', '激光', '精密测量', '检测设备', '干涉仪', '测量仪', '光度计', '折射率'],
    'ELEC': ['电子', '电气', '电路板', 'PCB', '元器件', '传感器', '示波器', '信号发生器'],
    'AUTO': ['汽车', '新能源', '电池', '充电', '电动车', '燃料电池', '动力系统'],
    'AERO': ['航空', '航天', '军工', '国防', '导弹', '卫星', '飞机', '无人机'],
    'CHEM': ['化工', '化学', '材料', '合成', '聚合物', '纳米材料', '高分子'],
    'BIO':  ['生物', '医疗', '基因', '细胞', '药物', '体外诊断', '病理', '检验科'],
    'ENV':  ['环境监测', '大气检测', '水质检测', '清洁能源', '废气', '污水'],
    'LAB':  ['实验室', '科研', '研发', '分析仪器', '检测仪器', '通用仪器'],
    'EDU_EQP': ['教学', '实训', '课程', '校园', '教育装备', '教学设备'],
    'IT':   ['信息化', '软件', '服务器', '网络', '云计算', '数字化', 'IT系统'],
}

def identify_industry(text):
    """从文本中识别行业分类，返回 (industry_code, industry_name)"""
    if pd.isna(text):
        return 'OTHER', '其他'
    s = str(text)
    for code, keywords in INDUSTRY_KEYWORDS.items():
        for kw in keywords:
            if kw in s:
                industry_names = {
                    'SEMI': '半导体/集成电路', 'OPT': '光学/精密仪器',
                    'ELEC': '电子/电气', 'AUTO': '汽车/新能源',
                    'AERO': '航空航天/军工', 'CHEM': '化工/材料',
                    'BIO': '生物/医疗', 'ENV': '环境/能源',
                    'LAB': '实验室/科研', 'EDU_EQP': '教育设备',
                    'IT': '信息技术', 'OTHER': '其他',
                }
                return code, industry_names[code]
    return 'OTHER', '其他'


# ==================== 机构类型识别 ====================

ORG_RULES = {
    'MIL': ['部队', '军区', '武警', '公安', '消防救援', '边防', '海警', '警察', '监狱', '司法厅', '检察院', '法院', '军校', '军事'],
    'GOV': ['政府', '市政', '区政', '县政', '委员会', '管理局', '管委会', '办公室', '发展和改革', '人民代表大会', '政协', '纪委', '监察', '财政局', '统计局', '审计局', '税务局', '海关', '城管', '市监', '应急管理', '生态环境', '自然资源'],
    'EDU': ['大学', '学院', '学校', '中学', '小学', '幼儿园', '职业技术', '高职', '高中', '初中', '教育局', '教育厅', '教委', '研究生院'],
    'MED': ['医院', '卫生院', '卫生所', '诊所', '医疗中心', '疾病预防控制', '疾控', '卫生局', '卫计委', '血液中心', '急救中心', '妇幼保健'],
    'RES': ['研究院', '研究所', '科学院', '实验室', '工程院', '检验检测中心', '质量检测', '计量院', '科技园'],
    'ENT': ['有限公司', '股份公司', '集团', '工厂', '厂', '国有', '央企'],
}

ORG_NAMES = {
    'MIL': '军警部队', 'GOV': '政府机关', 'EDU': '教育机构',
    'MED': '医疗卫生', 'RES': '科研院所', 'ENT': '企业单位', 'OTH': '其他',
}

def identify_org_type(org_name):
    """识别采购单位机构类型"""
    if pd.isna(org_name):
        return 'OTH', '其他'
    s = str(org_name)
    for code in ['MIL', 'GOV', 'EDU', 'MED', 'RES', 'ENT']:
        for kw in ORG_RULES[code]:
            if kw in s:
                return code, ORG_NAMES[code]
    return 'OTH', '其他'


# ==================== 厂商名称标准化 ====================

# 常见公司后缀，用于清理
COMPANY_SUFFIXES = [
    r'(股份)?有限公司', r'股份公司', r'集团.*?公司', r'科技.*?公司',
    r'（.*?）', r'\(.*?\)', r'分公司', r'子公司', r'销售部', r'代理商',
]

def normalize_vendor(vendor_str):
    """标准化厂商/中标单位名称"""
    if pd.isna(vendor_str):
        return '未知'
    s = str(vendor_str).strip()
    # 提取括号前的主名称
    s = re.split(r'[（(]', s)[0].strip()
    # 去除常见后缀
    for suffix in COMPANY_SUFFIXES:
        s = re.sub(suffix, '', s).strip()
    return s if s else '未知'


# ==================== 产品参数提取 ====================

def extract_product_params(detail_str, keyword=None):
    """
    从产品详情/项目名称中提取产品参数
    
    返回: {
        'model': 产品型号,
        'quantity': 数量,
        'specs': 技术规格摘要,
        'keyword_match': 是否匹配检索关键词
    }
    """
    if pd.isna(detail_str):
        return {'model': '', 'quantity': '', 'specs': '', 'keyword_match': False}
    
    s = str(detail_str)
    
    # 提取产品型号（字母+数字组合）
    model_matches = re.findall(r'\b[A-Za-z][A-Za-z0-9\-_]{2,15}\b', s)
    model = ', '.join(model_matches[:3]) if model_matches else ''
    
    # 提取数量
    qty_match = re.search(r'(\d+)\s*[台套件组批]', s)
    quantity = f"{qty_match.group(1)}{qty_match.group(0)[-1]}" if qty_match else ''
    
    # 提取规格参数（精度、范围、分辨率等）
    specs = []
    for param in ['精度', '分辨率', '测量范围', '量程', '频率', '功率', '电压', '电流']:
        m = re.search(rf'{param}[：:]\s*([^\s,，;；]{1,20})', s)
        if m:
            specs.append(f"{param}: {m.group(1)}")
    
    return {
        'model': model,
        'quantity': quantity,
        'specs': '; '.join(specs[:3]),
        'keyword_match': keyword.lower() in s.lower() if keyword else True,
    }


# ==================== 批量提炼函数 ====================

def enrich_dataframe(df, project_col='项目名称', buyer_col='采购单位',
                     vendor_col='中标单位', detail_col='产品详情',
                     amount_col='金额_万元', keyword=None):
    """
    对 DataFrame 批量提炼6个核心维度信息
    """
    df = df.copy()
    
    # 1. 行业识别（从项目名称）
    if project_col in df.columns:
        industry_result = df[project_col].apply(identify_industry)
        df['行业代码'] = [r[0] for r in industry_result]
        df['行业名称'] = [r[1] for r in industry_result]
    
    # 2. 机构类型（从采购单位）
    if buyer_col in df.columns:
        org_result = df[buyer_col].apply(identify_org_type)
        df['机构类型代码'] = [r[0] for r in org_result]
        df['机构类型'] = [r[1] for r in org_result]
    
    # 3. 厂商标准化
    if vendor_col in df.columns:
        df['厂商名称'] = df[vendor_col].apply(normalize_vendor)
    
    # 4. 产品参数提取
    detail_source = detail_col if detail_col in df.columns else (project_col if project_col in df.columns else None)
    if detail_source:
        params = df[detail_source].apply(lambda x: extract_product_params(x, keyword))
        df['产品型号'] = [p['model'] for p in params]
        df['数量'] = [p['quantity'] for p in params]
        df['技术规格'] = [p['specs'] for p in params]
    
    return df
