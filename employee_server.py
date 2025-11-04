#!/usr/bin/env python3
"""
员工查询 MCP 服务器 - 通过工号查询员工姓名

功能：
- 提供员工查询工具
- 返回随机2-3个中文字符作为员工姓名
- 支持 SSE 传输模式
"""

import random
from mcp.server import FastMCP

# 创建 MCP 服务器实例
mcp = FastMCP("employee_server", port = 8001)

# 随机中文字符生成
def generate_random_chinese_name(length: int = None) -> str:
    """生成随机中文字符作为姓名"""
    if length is None:
        length = random.randint(2, 3)  # 随机2-3个字
    
    # 常用中文字符范围（基本汉字）
    chinese_chars = []
    for code_point in range(0x4E00, 0x9FFF):  # CJK Unified Ideographs
        chinese_chars.append(chr(code_point))
    
    # 随机选择字符
    name = ''.join(random.choices(chinese_chars, k=length))
    return name

@mcp.tool()
async def query_employee(employee_id: str) -> str:
    """通过工号查询员工姓名"""
    if not employee_id:
        return "错误：请提供员工工号"
    
    # 生成随机中文姓名
    employee_name = generate_random_chinese_name()
    
    return f"工号 {employee_id} 对应的员工姓名是：{employee_name}\n\n员工信息：\n- 工号：{employee_id}\n- 姓名：{employee_name}\n- 部门：随机分配部门\n- 状态：在职"

@mcp.tool()
async def list_employees(department: str = None) -> str:
    """列出所有员工信息（示例数据）"""
    # 生成示例员工数据
    departments = ["技术部", "销售部", "人事部", "财务部"]
    if department and department in departments:
        departments = [department]
    
    employees = []
    for dept in departments:
        for i in range(3):  # 每个部门生成3个员工
            emp_id = f"{dept[:2]}{random.randint(1000, 9999)}"
            emp_name = generate_random_chinese_name()
            employees.append({
                "工号": emp_id,
                "姓名": emp_name,
                "部门": dept,
                "状态": "在职"
            })
    
    result = f"员工列表（部门：{department or '全部'}）\n\n"
    for emp in employees:
        result += f"- {emp['工号']} | {emp['姓名']} | {emp['部门']} | {emp['状态']}\n"
    
    return result

@mcp.tool()
async def get_employee_location(employee_id: str) -> str:
    """获取员工的当前位置（测试工具）"""
    # 硬编码的位置映射，用于测试工具调用
    location_mapping = {
        "D0001": "北京总部A座3楼会议室",
        "D0002": "成都分公司2楼办公室", 
        "D0003": "纽约办事处1楼接待室",
        "D0004": "深圳研发中心4楼实验室",
        "D0005": "上海总部B座5楼工位"
    }
    
    if employee_id in location_mapping:
        return f"工号{employee_id}的员工目前位于{location_mapping[employee_id]}。"
    else:
        return f"未找到工号{employee_id}的位置信息。已知工号：D0001(北京总部A座3楼会议室), D0002(成都分公司2楼办公室), D0003(纽约办事处1楼接待室), D0004(深圳研发中心4楼实验室), D0005(上海总部B座5楼工位)"

# 关键：不要加多余的 print，否则破坏 JSON-RPC 协议！
if __name__ == "__main__":
    mcp.run(transport="sse")
