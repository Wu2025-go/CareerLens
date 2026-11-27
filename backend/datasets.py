"""岗位样本缓存、来源筛选和可复核的数据版本。"""
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from typing import Literal

import pandas as pd
from fastapi import HTTPException

DatasetScope = Literal['real', 'synthetic', 'all']
SCOPES = {'real': '实采样本', 'synthetic': '仿真测试样本', 'all': '混合测试样本'}
REQUIRED_COLUMNS = {'job_id', 'job_title', 'company_name', 'city', 'salary_min',
                    'salary_max', 'education', 'experience', 'job_description',
                    'skills', 'publish_date', 'source', 'job_category'}


@lru_cache(maxsize=4)
def _read_dataset(path, modified, size):
    data = Path(path).read_bytes()
    for encoding in ('utf-8-sig', 'gb18030'):
        try:
            frame = pd.read_csv(path, encoding=encoding, keep_default_na=False)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError('岗位文件编码无法识别，请使用 UTF-8 CSV。')
    if not REQUIRED_COLUMNS.issubset(frame.columns):
        raise ValueError('岗位文件缺少字段：' + '、'.join(sorted(REQUIRED_COLUMNS - set(frame.columns))))
    ids = frame.job_id.astype(str).str.strip()
    if ids.eq('').any() or ids.duplicated().any():
        raise ValueError('岗位编号不能为空或重复。')
    if 'data_origin' not in frame:
        # 不根据编号猜测用户日后导入的数据来源。
        frame['data_origin'] = 'unverified'
    frame['data_origin'] = frame.data_origin.astype(str).str.strip().str.lower()
    if not set(frame.data_origin).issubset({'real', 'synthetic', 'unverified'}):
        raise ValueError('data_origin 只能是 real、synthetic 或 unverified。')
    frame.attrs.update(dataset_version=sha256(data).hexdigest()[:12], dataset_file=Path(path).name)
    return frame


def read_dataset(path):
    path = Path(path)
    try:
        stat = path.stat()
        return _read_dataset(str(path.resolve()), stat.st_mtime_ns, stat.st_size).copy()
    except (OSError, ValueError, pd.errors.ParserError) as exc:
        raise HTTPException(503, f'岗位数据暂时不可用：{exc}') from exc


def scope_dataset(frame, scope='real'):
    if scope not in SCOPES:
        raise HTTPException(422, '请选择 real、synthetic 或 all 数据范围。')
    counts = frame['data_origin'].value_counts().to_dict() if 'data_origin' in frame else {'unverified': len(frame)}
    # 兼容测试用的内存表；来源未标注会在元数据中明确说明。
    if scope != 'all' and 'data_origin' in frame:
        selected = frame.loc[frame.data_origin == scope].copy()
    else:
        selected = frame.copy()
    selected.attrs.update(frame.attrs)
    selected.attrs.update(dataset_scope=scope, dataset_total=len(frame), origin_counts=counts)
    return selected


def dataset_metadata(frame):
    dates = pd.to_datetime(frame.get('publish_date', pd.Series(dtype=str)), errors='coerce').dropna()
    origins = frame.attrs.get('origin_counts')
    if origins is None:
        origins = frame.data_origin.value_counts().to_dict() if 'data_origin' in frame else {'unverified': len(frame)}
    scope = frame.attrs.get('dataset_scope', 'real')
    return {
        'dataset_version': frame.attrs.get('dataset_version', 'in-memory'),
        'dataset_file': frame.attrs.get('dataset_file', 'jobs_sample.csv'),
        'dataset_scope': scope,
        'dataset_label': SCOPES[scope],
        'sample_count': int(len(frame)),
        'total_count': int(frame.attrs.get('dataset_total', len(frame))),
        'origin_counts': {key: int(origins.get(key, 0)) for key in ('real', 'synthetic', 'unverified')},
        'publish_date_start': dates.min().date().isoformat() if len(dates) else None,
        'publish_date_end': dates.max().date().isoformat() if len(dates) else None,
        'notice': ('来源分类依据团队提供的采集与扩充说明；实采样本尚缺逐岗位原网页链接。'
                   if scope == 'real' else '当前包含仿真记录，仅供功能与规模测试，不代表真实招聘市场。'),
    }


def attach_metadata(result, frame):
    return {**result, 'dataset': dataset_metadata(frame)}
