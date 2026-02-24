import pandas as pd
import os
from datetime import datetime
from typing import List, Dict, Optional, Callable
from pathlib import Path
import yaml
import json


class ExcelProcessor:
    """Excel数据自动处理器 - 合并多表、生成报表"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        self.data_dir = self.config.get('data_dir', 'data/excel')
        self.output_dir = self.config.get('output_dir', 'output')
        self._ensure_dirs()
        
    def _load_config(self, path: str) -> dict:
        """加载配置文件"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"配置文件 {path} 未找到，使用默认配置")
            return self._default_config()
    
    def _default_config(self) -> dict:
        """默认配置"""
        return {
            'data_dir': 'data/excel',
            'output_dir': 'output',
            'excel': {
                'default_sheet': 0,
                'header_row': 0,
                'encoding': 'utf-8'
            }
        }
    
    def _ensure_dirs(self):
        """确保目录存在"""
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
    
    def read_excel(self, filepath: str, **kwargs) -> Optional[pd.DataFrame]:
        """
        读取Excel文件
        
        Args:
            filepath: Excel文件路径
            **kwargs: 传递给pd.read_excel的额外参数
            
        Returns:
            DataFrame 或 None
        """
        try:
            excel_config = self.config.get('excel', {})
            params = {
                'sheet_name': kwargs.get('sheet_name', excel_config.get('default_sheet', 0)),
                'header': kwargs.get('header', excel_config.get('header_row', 0)),
            }
            params.update(kwargs)
            
            df = pd.read_excel(filepath, **params)
            print(f"✅ 成功读取: {filepath} ({len(df)} 行 x {len(df.columns)} 列)")
            return df
            
        except Exception as e:
            print(f"❌ 读取失败 {filepath}: {e}")
            return None
    
    def read_multiple(self, filepaths: List[str], **kwargs) -> List[pd.DataFrame]:
        """
        读取多个Excel文件
        
        Args:
            filepaths: 文件路径列表
            **kwargs: 额外参数
            
        Returns:
            DataFrame列表
        """
        dfs = []
        for filepath in filepaths:
            df = self.read_excel(filepath, **kwargs)
            if df is not None:
                dfs.append(df)
        return dfs
    
    def merge_sheets(self, filepaths: List[str], 
                     merge_columns: Optional[List[str]] = None,
                     add_source_column: bool = True) -> pd.DataFrame:
        """
        合并多个Excel表格
        
        Args:
            filepaths: 文件路径列表
            merge_columns: 合并时保留的列，None则保留所有
            add_source_column: 是否添加来源文件列
            
        Returns:
            合并后的DataFrame
        """
        all_data = []
        
        for filepath in filepaths:
            df = self.read_excel(filepath)
            if df is None:
                continue
            
            # 选择指定列
            if merge_columns:
                available_cols = [c for c in merge_columns if c in df.columns]
                df = df[available_cols]
            
            # 添加来源列
            if add_source_column:
                df['数据来源'] = Path(filepath).name
            
            all_data.append(df)
        
        if not all_data:
            return pd.DataFrame()
        
        merged = pd.concat(all_data, ignore_index=True)
        print(f"📊 合并完成: 共 {len(merged)} 行")
        return merged
    
    def merge_by_key(self, left_df: pd.DataFrame, right_df: pd.DataFrame,
                     left_key: str, right_key: Optional[str] = None,
                     how: str = 'inner') -> pd.DataFrame:
        """
        按关键联合并两个表格
        
        Args:
            left_df: 左表
            right_df: 右表
            left_key: 左表关键列
            right_key: 右表关键列，None则与left_key相同
            how: 合并方式 ('inner', 'outer', 'left', 'right')
            
        Returns:
            合并后的DataFrame
        """
        if right_key is None:
            right_key = left_key
            
        try:
            merged = pd.merge(left_df, right_df, 
                            left_on=left_key, right_on=right_key, 
                            how=how, suffixes=('', '_右表'))
            print(f"🔗 联合完成: {len(merged)} 行")
            return merged
        except Exception as e:
            print(f"❌ 联合失败: {e}")
            return pd.DataFrame()
    
    def clean_data(self, df: pd.DataFrame, 
                   remove_duplicates: bool = True,
                   fill_na: Optional[Dict] = None) -> pd.DataFrame:
        """
        数据清洗
        
        Args:
            df: 输入DataFrame
            remove_duplicates: 是否删除重复行
            fill_na: 填充空值的配置 {列名: 填充值}
            
        Returns:
            清洗后的DataFrame
        """
        original_len = len(df)
        
        # 删除完全重复的行
        if remove_duplicates:
            df = df.drop_duplicates()
            print(f"🧹 删除重复行: {original_len} → {len(df)}")
        
        # 填充空值
        if fill_na:
            for col, value in fill_na.items():
                if col in df.columns:
                    null_count = df[col].isnull().sum()
                    df[col] = df[col].fillna(value)
                    print(f"📝 填充 '{col}': {null_count} 个空值 → '{value}'")
        
        return df
    
    def generate_summary(self, df: pd.DataFrame, 
                        group_by: Optional[str] = None) -> Dict:
        """
        生成数据摘要
        
        Args:
            df: 输入DataFrame
            group_by: 分组列名
            
        Returns:
            摘要统计字典
        """
        summary = {
            '总行数': len(df),
            '总列数': len(df.columns),
            '列名': list(df.columns),
            '数据类型': {col: str(dtype) for col, dtype in df.dtypes.items()},
        }
        
        # 数值列统计
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        if numeric_cols:
            summary['数值统计'] = df[numeric_cols].describe().to_dict()
        
        # 分组统计
        if group_by and group_by in df.columns:
            summary['分组统计'] = df.groupby(group_by).size().to_dict()
        
        return summary
    
    def create_pivot_table(self, df: pd.DataFrame,
                          values: str,
                          index: str,
                          columns: Optional[str] = None,
                          aggfunc: str = 'sum') -> pd.DataFrame:
        """
        创建数据透视表
        
        Args:
            df: 输入DataFrame
            values: 值列
            index: 行索引列
            columns: 列索引列
            aggfunc: 聚合函数
            
        Returns:
            透视表DataFrame
        """
        try:
            pivot = pd.pivot_table(df, values=values, index=index, 
                                  columns=columns, aggfunc=aggfunc,
                                  fill_value=0)
            print(f"📊 透视表创建完成: {pivot.shape}")
            return pivot
        except Exception as e:
            print(f"❌ 透视表创建失败: {e}")
            return pd.DataFrame()
    
    def export_excel(self, df: pd.DataFrame, filename: str,
                     sheet_name: str = 'Sheet1',
                     index: bool = False) -> str:
        """
        导出到Excel
        
        Args:
            df: 输入DataFrame
            filename: 输出文件名
            sheet_name: 工作表名称
            index: 是否包含索引
            
        Returns:
            输出文件路径
        """
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            df.to_excel(filepath, sheet_name=sheet_name, index=index)
            print(f"💾 已导出: {filepath}")
            return filepath
        except Exception as e:
            print(f"❌ 导出失败: {e}")
            return ""
    
    def export_multi_sheets(self, data_dict: Dict[str, pd.DataFrame],
                           filename: str) -> str:
        """
        导出多个工作表到单个Excel文件
        
        Args:
            data_dict: {工作表名: DataFrame}
            filename: 输出文件名
            
        Returns:
            输出文件路径
        """
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                for sheet_name, df in data_dict.items():
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            print(f"💾 多工作表导出完成: {filepath} ({len(data_dict)} 个工作表)")
            return filepath
        except Exception as e:
            print(f"❌ 导出失败: {e}")
            return ""
    
    def generate_report(self, df: pd.DataFrame, 
                       report_name: str = None) -> str:
        """
        生成完整报表（包含摘要、透视表等）
        
        Args:
            df: 输入DataFrame
            report_name: 报表名称
            
        Returns:
            报表文件路径
        """
        if report_name is None:
            report_name = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        sheets = {}
        
        # 原始数据
        sheets['原始数据'] = df
        
        # 数据摘要
        summary_df = pd.DataFrame([self.generate_summary(df)])
        sheets['数据摘要'] = summary_df
        
        # 数值列统计
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        if numeric_cols:
            sheets['数值统计'] = df[numeric_cols].describe()
        
        # 导出
        return self.export_multi_sheets(sheets, f"{report_name}.xlsx")
    
    def batch_process(self, input_pattern: str, 
                     processor: Callable[[pd.DataFrame], pd.DataFrame],
                     output_suffix: str = "_processed"):
        """
        批量处理Excel文件
        
        Args:
            input_pattern: 输入文件匹配模式 (如 "data/*.xlsx")
            processor: 处理函数
            output_suffix: 输出文件后缀
        """
        import glob
        
        files = glob.glob(input_pattern)
        print(f"📁 找到 {len(files)} 个文件待处理")
        
        for filepath in files:
            df = self.read_excel(filepath)
            if df is None:
                continue
            
            # 处理数据
            processed = processor(df)
            
            # 生成输出文件名
            base_name = Path(filepath).stem
            output_name = f"{base_name}{output_suffix}.xlsx"
            
            self.export_excel(processed, output_name)


def example_processor():
    """示例数据处理函数"""
    def processor(df: pd.DataFrame) -> pd.DataFrame:
        # 删除空行
        df = df.dropna(how='all')
        # 删除重复行
        df = df.drop_duplicates()
        # 添加处理时间列
        df['处理时间'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return df
    
    return processor


def main():
    """主函数 - 演示功能"""
    processor = ExcelProcessor()
    
    # 创建示例数据
    print("📝 创建示例数据...")
    
    # 示例数据1
    df1 = pd.DataFrame({
        '产品': ['A', 'B', 'C', 'A', 'B'],
        '销量': [100, 150, 200, 120, 180],
        '价格': [10.5, 20.0, 15.5, 10.5, 20.0],
        '日期': ['2024-01-01'] * 5
    })
    
    # 示例数据2
    df2 = pd.DataFrame({
        '产品': ['D', 'E', 'F'],
        '销量': [80, 90, 110],
        '价格': [25.0, 30.0, 12.0],
        '日期': ['2024-01-01'] * 3
    })
    
    # 保存示例数据
    sample_dir = os.path.join(processor.data_dir, 'samples')
    os.makedirs(sample_dir, exist_ok=True)
    
    df1.to_excel(os.path.join(sample_dir, 'sample1.xlsx'), index=False)
    df2.to_excel(os.path.join(sample_dir, 'sample2.xlsx'), index=False)
    
    print("\n📊 演示: 合并多个表格")
    merged = processor.merge_sheets([
        os.path.join(sample_dir, 'sample1.xlsx'),
        os.path.join(sample_dir, 'sample2.xlsx')
    ])
    print(merged)
    
    print("\n📈 演示: 创建透视表")
    pivot = processor.create_pivot_table(merged, values='销量', index='产品', aggfunc='sum')
    print(pivot)
    
    print("\n🧹 演示: 数据清洗")
    cleaned = processor.clean_data(merged, fill_na={'价格': 0})
    
    print("\n📋 演示: 生成摘要")
    summary = processor.generate_summary(cleaned, group_by='产品')
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=str))
    
    print("\n💾 演示: 生成报表")
    report_path = processor.generate_report(cleaned, "demo_report")
    
    print(f"\n✅ 演示完成！报表已保存至: {report_path}")


if __name__ == "__main__":
    main()
