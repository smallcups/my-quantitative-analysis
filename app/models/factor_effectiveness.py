from app.extensions import db
from sqlalchemy import Column, String, Date, DECIMAL, DateTime, Integer, Index, JSON
from datetime import datetime


class FactorEffectiveness(db.Model):
    """因子有效性评估表 - 存储Rank IC分析结果"""
    __tablename__ = 'factor_effectiveness'

    factor_id = Column(String(50), primary_key=True, comment='因子ID')
    evaluation_date = Column(Date, primary_key=True, comment='评估日期')
    forward_period = Column(Integer, primary_key=True, comment='前瞻收益周期(天)')

    ic_mean = Column(DECIMAL(10, 6), comment='IC均值')
    ic_std = Column(DECIMAL(10, 6), comment='IC标准差')
    ic_ir = Column(DECIMAL(10, 6), comment='IC信息比率(IC均值/IC标准差)')
    ic_win_rate = Column(DECIMAL(5, 2), comment='IC胜率(正值占比%)')
    latest_ic = Column(DECIMAL(10, 6), comment='最新一期IC值')
    sample_count = Column(Integer, comment='有效样本数')
    factor_direction = Column(String(10), comment='因子方向(positive/negative)')
    extra_info = Column(JSON, comment='额外信息(IC序列等)')
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')

    __table_args__ = (
        Index('idx_eff_factor_date', 'factor_id', 'evaluation_date'),
        Index('idx_eff_date_period', 'evaluation_date', 'forward_period'),
    )

    def to_dict(self):
        return {
            'factor_id': self.factor_id,
            'evaluation_date': self.evaluation_date.isoformat() if self.evaluation_date else None,
            'forward_period': self.forward_period,
            'ic_mean': float(self.ic_mean) if self.ic_mean else None,
            'ic_std': float(self.ic_std) if self.ic_std else None,
            'ic_ir': float(self.ic_ir) if self.ic_ir else None,
            'ic_win_rate': float(self.ic_win_rate) if self.ic_win_rate else None,
            'latest_ic': float(self.latest_ic) if self.latest_ic else None,
            'sample_count': self.sample_count,
            'factor_direction': self.factor_direction,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f'<FactorEffectiveness {self.factor_id} @{self.evaluation_date} P{self.forward_period}>'
