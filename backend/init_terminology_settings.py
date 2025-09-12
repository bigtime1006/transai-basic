#!/usr/bin/env python3
"""
术语库分类分组功能系统设置初始化脚本
执行此脚本将添加必要的系统配置项
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from app.database import DATABASE_URL

def init_system_settings():
    """初始化系统设置"""
    print("开始初始化术语库分类分组功能系统设置...")
    
    # 获取数据库连接
    database_url = os.getenv("DATABASE_URL", DATABASE_URL)
    engine = create_engine(database_url)
    
    # 需要添加的系统设置
    settings_to_add = [
        {
            "category": "terminology",
            "key": "terminology_categories_enabled",
            "value": "true",
            "value_type": "bool",
            "description": "是否启用术语分类功能",
            "is_public": True,
            "is_editable": True
        },
        {
            "category": "terminology",
            "key": "terminology_max_categories_per_translation",
            "value": "10",
            "value_type": "int",
            "description": "单次翻译最大可选分类数",
            "is_public": True,
            "is_editable": True
        },
        {
            "category": "terminology",
            "key": "terminology_default_categories",
            "value": "[]",
            "value_type": "json",
            "description": "默认选中的分类ID列表",
            "is_public": True,
            "is_editable": True
        }
    ]
    
    try:
        with engine.connect() as conn:
            for setting in settings_to_add:
                # 检查设置是否已存在
                result = conn.execute(text(
                    "SELECT id FROM system_settings WHERE category = :category AND key = :key"
                ), {"category": setting["category"], "key": setting["key"]})
                
                existing = result.fetchone()
                
                if existing:
                    print(f"设置 {setting['key']} 已存在，跳过")
                    continue
                
                # 插入新设置
                insert_sql = """
                INSERT INTO system_settings (category, key, value, value_type, description, is_public, is_editable)
                VALUES (:category, :key, :value, :value_type, :description, :is_public, :is_editable)
                """
                
                conn.execute(text(insert_sql), setting)
                print(f"✓ 添加设置: {setting['key']} = {setting['value']}")
            
            conn.commit()
            print("\n系统设置初始化完成！")
            return True
            
    except Exception as e:
        print(f"初始化过程中发生错误: {e}")
        return False
    finally:
        engine.dispose()

def verify_settings():
    """验证设置是否正确添加"""
    print("\n验证系统设置...")
    
    database_url = os.getenv("DATABASE_URL", DATABASE_URL)
    engine = create_engine(database_url)
    
    try:
        with engine.connect() as conn:
            # 检查新添加的设置
            settings_to_check = [
                "terminology_categories_enabled",
                "terminology_max_categories_per_translation",
                "terminology_default_categories"
            ]
            
            for key in settings_to_check:
                result = conn.execute(text(
                    "SELECT value, value_type, description FROM system_settings WHERE key = :key"
                ), {"key": key})
                
                setting = result.fetchone()
                if setting:
                    print(f"✓ 设置 {key}: {setting[0]} ({setting[1]}) - {setting[2]}")
                else:
                    print(f"✗ 设置 {key} 未找到")
            
            # 显示所有术语相关设置
            print("\n所有术语相关系统设置:")
            result = conn.execute(text(
                "SELECT key, value, description FROM system_settings WHERE category = 'terminology' ORDER BY key"
            ))
            
            for row in result:
                print(f"  {row[0]}: {row[1]} - {row[2]}")
                
    except Exception as e:
        print(f"验证过程中发生错误: {e}")
        return False
    finally:
        engine.dispose()
    
    return True

if __name__ == "__main__":
    print("术语库分类分组功能系统设置初始化工具")
    print("=" * 50)
    
    # 确认执行
    confirm = input("确认初始化系统设置？这将添加新的配置项 (y/N): ").strip().lower()
    if confirm != 'y':
        print("取消初始化")
        sys.exit(0)
    
    # 执行初始化
    if init_system_settings():
        # 验证结果
        verify_settings()
        print("\n初始化完成！请检查上述验证结果。")
    else:
        print("\n初始化失败！请检查错误信息。")
        sys.exit(1)
