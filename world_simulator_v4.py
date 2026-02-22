"""
世界观模拟器 v4.0 - 深度数值关联系统

重构后的模块化架构入口文件

使用方法:
    python world_simulator_v4.py
    
或作为模块导入:
    from modules import Simulator
    
    sim = Simulator()
    sim.start_world("agi")
    result = sim.next_year()
"""

from modules import Simulator, WorldCategory, list_all_presets


def print_banner():
    """打印欢迎横幅"""
    print("=" * 70)
    print("🌍 世界观模拟器 v4.0 - 深度数值关联系统")
    print("=" * 70)
    print()


def print_world_selection():
    """打印世界观选择菜单"""
    presets = list_all_presets()
    
    print("请选择世界观:\n")
    
    # 按类别分组
    categories = {}
    for p in presets:
        cat_name = p.category.value
        if cat_name not in categories:
            categories[cat_name] = []
        categories[cat_name].append(p)
    
    # 类别显示名称映射
    cat_display = {
        "history": "📜 历史类",
        "scifi": "🚀 科幻类",
        "fantasy": "🐉 东方玄幻",
        "magic": "🧙 西方魔幻",
        "apocalypse": "☠️ 末日生存",
        "modern": "🏙️ 现代都市"
    }
    
    for cat_key, cat_presets in categories.items():
        print(f"\n{cat_display.get(cat_key, cat_key)}")
        print("-" * 40)
        for p in cat_presets:
            print(f"  [{p.id:15s}] {p.icon} {p.name}")


def print_state(sim):
    """打印当前状态"""
    state = sim.get_state()
    if not state:
        return
    
    print(f"\n{'='*70}")
    print(f"📅 {state.year}{state.year_suffix}")
    print(f"{'='*70}")
    
    stats = state.stats
    print(f"  ⚖️ 稳定: {stats['stability']:.0%}")
    print(f"  💰 繁荣: {stats['prosperity']:.0%}")
    print(f"  ⚖️ 平等: {stats['equality']:.0%}")
    print(f"  🕊️ 自由: {stats['freedom']:.0%}")
    print(f"  🔬 科技: {stats['tech']:.0%}")


def print_event_result(result):
    """打印事件结果"""
    if "error" in result:
        print(f"\n⚠️ {result['error']}")
        return
    
    event = result.get("event", {})
    
    print(f"\n{'='*70}")
    print(f"📅 事件: {event.get('name', '未知')}")
    print(f"   {event.get('description', '')}")
    print(f"{'='*70}")
    
    # 显示直接影响
    changes = result.get("changes", [])
    if changes:
        print("\n   直接影响:")
        for change in changes:
            emoji = change.get("emoji", "")
            name = change.get("name", change.get("key", ""))
            old_val = change.get("old", 0)
            new_val = change.get("new", 0)
            delta = change.get("delta", 0)
            arrow = "↑" if delta > 0 else "↓"
            print(f"     {emoji} {name}: {old_val:.0%} {arrow} {new_val:.0%}")
    
    # 显示连锁反应
    cascades = result.get("cascades", [])
    if cascades:
        print("\n   系统反应:")
        for cascade in cascades:
            desc = cascade.get("desc", "")
            print(f"     ⚡ {desc}")


def print_choices(result):
    """打印选择选项"""
    event = result.get("event", {})
    choices = result.get("choices", [])
    
    print(f"\n{'='*70}")
    print(f"🚨 重大历史节点: {event.get('name', '')}")
    print(f"   {event.get('description', '')}")
    print(f"{'='*70}")
    print("\n请选择应对方式:\n")
    
    for i, choice in enumerate(choices, 1):
        print(f"  [{i}] {choice.get('title', '')}")
        print(f"      {choice.get('description', '')}")
        print()
    
    return choices


def get_choice_input(choices):
    """获取用户选择"""
    while True:
        try:
            choice_num = input("请输入选项编号 (1-3): ").strip()
            choice_idx = int(choice_num) - 1
            if 0 <= choice_idx < len(choices):
                return choices[choice_idx].get("id")
            else:
                print("无效的选项，请重新输入")
        except ValueError:
            print("请输入数字")


def main():
    """主程序"""
    print_banner()
    
    # 显示可用世界观
    print_world_selection()
    
    # 获取用户选择
    print()
    preset_id = input("请输入世界观ID (默认: agi): ").strip()
    if not preset_id:
        preset_id = "agi"
    
    # 初始化模拟器
    sim = Simulator()
    
    try:
        sim.start_world(preset_id)
    except ValueError as e:
        print(f"\n❌ 错误: {e}")
        return
    
    # 打印初始状态
    print_state(sim)
    
    # 主循环
    while not sim.is_game_over():
        print("\n" + "-" * 70)
        action = input("按Enter推进一年，输入q退出: ").strip().lower()
        
        if action == 'q':
            break
        
        # 推进一年
        result = sim.next_year()
        
        if "error" in result:
            print(f"\n⚠️ {result['error']}")
            continue
        
        # 处理世界线事件（需要选择）
        if result.get("type") == "worldline":
            choices = print_choices(result)
            choice_id = get_choice_input(choices)
            result = sim.make_choice(choice_id)
            print_event_result(result)
        else:
            print_event_result(result)
        
        # 打印当前状态
        print_state(sim)
    
    # 游戏结束
    if sim.is_game_over():
        state = sim.get_state()
        print(f"\n{'='*70}")
        print(f"{state.ending}")
        print(f"{'='*70}")
    
    # 打印统计
    summary = sim.get_history_summary()
    print(f"\n📊 游戏统计:")
    print(f"  总年数: {summary.get('total_years', 0)}")
    print(f"  世界线事件: {summary.get('worldline_events', 0)}")
    print(f"  做出的选择: {summary.get('choices_made', 0)}")
    
    # 是否导出历史
    print()
    export = input("是否导出历史记录到文件? (y/n): ").strip().lower()
    if export == 'y':
        filename = f"history_{preset_id}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(sim.get_history_text())
        print(f"历史记录已保存到: {filename}")
    
    print("\n感谢使用世界观模拟器!")


if __name__ == "__main__":
    main()
