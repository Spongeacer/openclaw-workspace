#!/usr/bin/env python3
"""简单的项目结构测试 - 验证文件和基本语法"""
import sys
from pathlib import Path

# 项目根目录
PROJECT_DIR = Path(__file__).parent.parent

def test_file_exists():
    """测试关键文件是否存在"""
    print("=" * 60)
    print("Testing Project Structure")
    print("=" * 60)
    
    required_files = [
        "main.py",
        "requirements.txt",
        "README.md",
        ".gitignore",
        "config/__init__.py",
        "config/.env.example",
        "config/settings.yaml",
        "src/__init__.py",
        "src/downloader.py",
        "src/transcriber.py",
        "src/translator.py",
        "src/tts_engine.py",
        "src/pipeline.py",
        "src/utils/__init__.py",
    ]
    
    missing = []
    for file in required_files:
        path = PROJECT_DIR / file
        if path.exists():
            size = path.stat().st_size
            print(f"✓ {file:<40} ({size:>6} bytes)")
        else:
            print(f"✗ {file:<40} MISSING")
            missing.append(file)
    
    if missing:
        print(f"\n✗ Missing {len(missing)} files!")
        return False
    
    print(f"\n✓ All {len(required_files)} files present!")
    return True


def test_python_syntax():
    """测试 Python 文件语法"""
    print("\n" + "=" * 60)
    print("Testing Python Syntax")
    print("=" * 60)
    
    import py_compile
    
    python_files = [
        "main.py",
        "config/__init__.py",
        "src/__init__.py",
        "src/downloader.py",
        "src/transcriber.py",
        "src/translator.py",
        "src/tts_engine.py",
        "src/pipeline.py",
    ]
    
    errors = []
    for file in python_files:
        path = PROJECT_DIR / file
        try:
            py_compile.compile(str(path), doraise=True)
            print(f"✓ {file}")
        except py_compile.PyCompileError as e:
            print(f"✗ {file}: {e}")
            errors.append((file, e))
    
    if errors:
        print(f"\n✗ {len(errors)} files have syntax errors!")
        return False
    
    print(f"\n✓ All {len(python_files)} files compile successfully!")
    return True


def test_imports():
    """测试关键导入"""
    print("\n" + "=" * 60)
    print("Testing Imports (without dependencies)")
    print("=" * 60)
    
    # 将项目根目录添加到路径
    sys.path.insert(0, str(PROJECT_DIR))
    
    results = []
    
    # 测试 utils（纯 Python，无外部依赖）
    try:
        from src.utils import validate_youtube_url, extract_video_id, format_duration
        print("✓ src.utils")
        results.append(("src.utils", True))
    except Exception as e:
        print(f"✗ src.utils: {e}")
        results.append(("src.utils", False))
    
    return all(r[1] for r in results)


def main():
    results = []
    
    results.append(("File Structure", test_file_exists()))
    results.append(("Python Syntax", test_python_syntax()))
    results.append(("Imports", test_imports()))
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{name:<20} {status}")
    
    all_passed = all(r[1] for r in results)
    
    print("=" * 60)
    if all_passed:
        print("All tests passed! ✓")
        return 0
    else:
        print("Some tests failed! ✗")
        return 1


if __name__ == "__main__":
    sys.exit(main())
