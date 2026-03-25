"""完整性检查模块 - 检查各阶段输出质量"""
import json
import re
from dataclasses import dataclass
from typing import List, Dict, Optional
from pathlib import Path


@dataclass
class CheckResult:
    """检查结果"""
    passed: bool
    stage: str
    message: str
    details: Dict = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}


class QualityChecker:
    """质量检查器"""
    
    # 专业名词白名单（应该保留英文的词汇）
    TECH_TERMS = {
        'agent', 'openclaw', 'ai', 'llm', 'gpt', 'api', 'gpu', 'tts', 'asr',
        'codex', 'prompt', 'token', 'model', 'lab', 'github', 'python', 'javascript',
        'web', 'app', 'internet', 'email', 'whatsapp', 'fedex', 'claude', 'anthropic',
        'google', 'microsoft', 'meta', 'openai', 'huggingface', 'pytorch', 'tensorflow',
        'aquin', 'adobe', 'cursor', 'copilot', 'chatgpt', 'gemini', 'llama'
    }
    
    # 人名白名单
    PERSON_NAMES = {
        'andrej karpathy', 'karpathy', 'andrej',
        'no priors', 'nopriors', 'no prior'
    }
    
    # 错误翻译模式（常见错误）
    TRANSLATION_ERRORS = [
        ('kpofi', 'Karpathy'),
        ('noprier', 'No Priors'),
        ('aquint', 'Aquin'),
        ('dobe', 'Adobe'),
        ('aquing', 'Aquin'),
    ]
    
    def __init__(self):
        self.issues = []
    
    def check_translation(self, segments: List) -> CheckResult:
        """
        检查翻译质量
        
        Returns:
            CheckResult with details containing issue list
        """
        issues = []
        warnings = []
        
        for i, seg in enumerate(segments):
            text = seg.text if hasattr(seg, 'text') else seg.get('text', '')
            text_lower = text.lower()
            
            # 检查 1: 专业名词是否被错误翻译
            for wrong, correct in self.TRANSLATION_ERRORS:
                if wrong in text_lower:
                    issues.append({
                        'type': 'translation_error',
                        'segment': i,
                        'text': text[:50] + '...',
                        'issue': f'发现错误翻译: "{wrong}" 应为 "{correct}"'
                    })
            
            # 检查 2: 是否有过多的"那么"、"就是"等翻译腔
            filler_words = text.count('那么') + text.count('就是') + text.count('其实')
            if filler_words > 3:
                warnings.append({
                    'type': 'translation_tone',
                    'segment': i,
                    'text': text[:50] + '...',
                    'issue': f'翻译腔较重（{filler_words}个填充词）'
                })
            
            # 检查 3: 段落长度
            if len(text) > 200:
                warnings.append({
                    'type': 'length',
                    'segment': i,
                    'text': text[:50] + '...',
                    'issue': f'段落过长 ({len(text)}字符)，建议切分'
                })
            
            # 检查 4: 情绪标签
            emotion = seg.emotion if hasattr(seg, 'emotion') else seg.get('emotion', '')
            if not emotion or emotion == '中性':
                warnings.append({
                    'type': 'emotion',
                    'segment': i,
                    'issue': '缺少情绪标签或情绪为中性'
                })
        
        # 汇总
        passed = len(issues) == 0
        message = f"翻译检查: {len(issues)}个错误, {len(warnings)}个警告"
        
        return CheckResult(
            passed=passed,
            stage='translation',
            message=message,
            details={'issues': issues, 'warnings': warnings}
        )
    
    def check_qa_pairs(self, qa_pairs: List[Dict]) -> CheckResult:
        """
        检查QA对质量
        
        Returns:
            CheckResult with details
        """
        issues = []
        warnings = []
        
        if not qa_pairs:
            return CheckResult(
                passed=False,
                stage='qa_pairs',
                message='QA对为空',
                details={'issues': [{'type': 'empty', 'issue': '没有QA对'}]}
            )
        
        # 统计
        total = len(qa_pairs)
        transitions = sum(1 for p in qa_pairs if p.get('is_transition', False))
        normal = total - transitions
        
        # 检查 1: Q/A 长度
        for i, pair in enumerate(qa_pairs):
            q_len = len(pair.get('question', ''))
            a_len = len(pair.get('answer', ''))
            
            if q_len < 10:
                issues.append({
                    'type': 'short_question',
                    'pair': i,
                    'issue': f'问题过短 ({q_len}字符)'
                })
            
            if a_len < 20 and not pair.get('is_transition'):
                warnings.append({
                    'type': 'short_answer',
                    'pair': i,
                    'issue': f'回答较短 ({a_len}字符)'
                })
            
            # 检查 2: 过渡段落比例
            if transitions > total * 0.3:
                warnings.append({
                    'type': 'too_many_transitions',
                    'issue': f'过渡段落占比过高 ({transitions}/{total})'
                })
            
            # 检查 3: 开场和结尾
            has_intro = any(p.get('is_transition') and i < 3 for i, p in enumerate(qa_pairs))
            has_outro = any(p.get('is_transition') and i > total - 3 for i, p in enumerate(qa_pairs))
            
            if not has_intro:
                warnings.append({'type': 'missing_intro', 'issue': '缺少开场包装'})
            if not has_outro:
                warnings.append({'type': 'missing_outro', 'issue': '缺少结尾包装'})
        
        passed = len(issues) == 0
        message = f"QA检查: {total}对 (正常{normal}, 过渡{transitions}), {len(issues)}个错误, {len(warnings)}个警告"
        
        return CheckResult(
            passed=passed,
            stage='qa_pairs',
            message=message,
            details={
                'total': total,
                'normal': normal,
                'transitions': transitions,
                'issues': issues,
                'warnings': warnings
            }
        )
    
    def check_audio(self, audio_path: Path, qa_pairs: List[Dict]) -> CheckResult:
        """
        检查音频完整性
        
        Args:
            audio_path: 音频文件路径
            qa_pairs: QA对列表（用于估算预期时长）
        
        Returns:
            CheckResult
        """
        import subprocess
        
        issues = []
        warnings = []
        
        # 检查文件存在
        if not audio_path.exists():
            return CheckResult(
                passed=False,
                stage='audio',
                message='音频文件不存在',
                details={'issues': [{'type': 'missing_file', 'path': str(audio_path)}]}
            )
        
        # 获取文件大小
        file_size = audio_path.stat().st_size
        if file_size < 1024 * 1024:  # < 1MB
            issues.append({
                'type': 'small_file',
                'issue': f'文件过小 ({file_size / 1024:.1f} KB)，可能不完整'
            })
        
        # 获取音频时长
        try:
            result = subprocess.run(
                ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                 '-of', 'default=noprint_wrappers=1:nokey=1', str(audio_path)],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                duration = float(result.stdout.strip())
                
                # 估算预期时长（每QA对约30秒）
                expected_duration = len(qa_pairs) * 30
                
                if duration < expected_duration * 0.5:
                    issues.append({
                        'type': 'short_duration',
                        'issue': f'音频时长过短 ({duration/60:.1f}分钟)，预期约{expected_duration/60:.1f}分钟'
                    })
                elif duration < expected_duration * 0.8:
                    warnings.append({
                        'type': 'partial_duration',
                        'issue': f'音频时长偏短 ({duration/60:.1f}分钟)，可能只生成了部分'
                    })
                
                # 检查声道
                result_ch = subprocess.run(
                    ['ffprobe', '-v', 'error', '-show_entries', 'stream=channels',
                     '-of', 'default=noprint_wrappers=1:nokey=1', str(audio_path)],
                    capture_output=True, text=True, timeout=10
                )
                if result_ch.returncode == 0:
                    channels = int(result_ch.stdout.strip().split('\n')[0])
                    if channels != 1:
                        warnings.append({
                            'type': 'not_mono',
                            'issue': f'不是单声道 ({channels}声道)，建议改为单声道'
                        })
                
                details = {
                    'duration': duration,
                    'file_size_mb': file_size / 1024 / 1024,
                    'expected_duration': expected_duration,
                    'qa_count': len(qa_pairs),
                    'issues': issues,
                    'warnings': warnings
                }
            else:
                issues.append({'type': 'ffprobe_failed', 'issue': '无法获取音频信息'})
                details = {'issues': issues, 'warnings': warnings}
        except Exception as e:
            issues.append({'type': 'exception', 'issue': f'检查异常: {e}'})
            details = {'issues': issues, 'warnings': warnings}
        
        passed = len(issues) == 0
        message = f"音频检查: {file_size/1024/1024:.2f}MB, {len(issues)}个错误, {len(warnings)}个警告"
        
        return CheckResult(
            passed=passed,
            stage='audio',
            message=message,
            details=details
        )
    
    def run_all_checks(self, segments: List, qa_pairs: List[Dict], audio_path: Path) -> List[CheckResult]:
        """运行所有检查"""
        results = []
        
        # 检查翻译
        if segments:
            results.append(self.check_translation(segments))
        
        # 检查QA
        if qa_pairs:
            results.append(self.check_qa_pairs(qa_pairs))
        
        # 检查音频
        if audio_path:
            results.append(self.check_audio(audio_path, qa_pairs))
        
        return results
    
    def generate_report(self, results: List[CheckResult]) -> str:
        """生成检查报告"""
        lines = [
            "=" * 70,
            "完整性检查报告",
            "=" * 70,
            ""
        ]
        
        all_passed = all(r.passed for r in results)
        
        for result in results:
            status = "✅ 通过" if result.passed else "❌ 未通过"
            lines.append(f"{status} [{result.stage.upper()}]")
            lines.append(f"  {result.message}")
            
            if result.details.get('issues'):
                lines.append("  错误:")
                for issue in result.details['issues'][:5]:  # 最多显示5个
                    lines.append(f"    - {issue.get('issue', str(issue))}")
            
            if result.details.get('warnings'):
                lines.append("  警告:")
                for warning in result.details['warnings'][:5]:
                    lines.append(f"    - {warning.get('issue', str(warning))}")
            
            lines.append("")
        
        lines.append("=" * 70)
        lines.append(f"总体状态: {'✅ 全部通过' if all_passed else '❌ 存在问题'}")
        lines.append("=" * 70)
        
        return "\n".join(lines)
