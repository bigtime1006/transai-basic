#!/usr/bin/env python3
"""
用户管理脚本
用于创建、删除和管理用户账号
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models import User, UserRole
from app.auth import get_password_hash
import argparse

def create_user(username: str, password: str, role: str = "user", quota: int = 10000):
    """创建新用户"""
    db = SessionLocal()
    try:
        # 检查用户是否已存在
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            print(f"用户 '{username}' 已存在")
            return False
        
        # 验证角色
        if role not in ["user", "admin"]:
            print(f"无效的角色: {role}，必须是 'user' 或 'admin'")
            return False
        
        # 创建用户
        hashed_password = get_password_hash(password)
        user = User(
            username=username,
            password=hashed_password,
            role=UserRole(role),
            quota=quota,
            status=True
        )
        db.add(user)
        db.commit()
        print(f"用户 '{username}' 创建成功")
        print(f"角色: {role}")
        print(f"配额: {quota}")
        return True
    except Exception as e:
        print(f"创建用户失败: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def delete_user(username: str):
    """删除用户"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            print(f"用户 '{username}' 不存在")
            return False
        
        if user.username == "admin":
            print("不能删除admin用户")
            return False
        
        db.delete(user)
        db.commit()
        print(f"用户 '{username}' 删除成功")
        return True
    except Exception as e:
        print(f"删除用户失败: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def list_users():
    """列出所有用户"""
    db = SessionLocal()
    try:
        users = db.query(User).all()
        print(f"\n总用户数: {len(users)}")
        print("-" * 60)
        print(f"{'ID':<4} {'用户名':<15} {'角色':<8} {'状态':<6} {'配额':<8}")
        print("-" * 60)
        for user in users:
            status = "启用" if user.status else "禁用"
            print(f"{user.id:<4} {user.username:<15} {user.role:<8} {status:<6} {user.quota:<8}")
        print("-" * 60)
    except Exception as e:
        print(f"获取用户列表失败: {e}")
    finally:
        db.close()

def change_password(username: str, new_password: str):
    """修改用户密码"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            print(f"用户 '{username}' 不存在")
            return False
        
        hashed_password = get_password_hash(new_password)
        user.password = hashed_password
        db.commit()
        print(f"用户 '{username}' 密码修改成功")
        return True
    except Exception as e:
        print(f"修改密码失败: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def main():
    parser = argparse.ArgumentParser(description="用户管理脚本")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # 创建用户命令
    create_parser = subparsers.add_parser("create", help="创建用户")
    create_parser.add_argument("username", help="用户名")
    create_parser.add_argument("password", help="密码")
    create_parser.add_argument("--role", choices=["user", "admin"], default="user", help="用户角色")
    create_parser.add_argument("--quota", type=int, default=10000, help="用户配额")
    
    # 删除用户命令
    delete_parser = subparsers.add_parser("delete", help="删除用户")
    delete_parser.add_argument("username", help="用户名")
    
    # 列出用户命令
    subparsers.add_parser("list", help="列出所有用户")
    
    # 修改密码命令
    change_pwd_parser = subparsers.add_parser("change-password", help="修改用户密码")
    change_pwd_parser.add_argument("username", help="用户名")
    change_pwd_parser.add_argument("new_password", help="新密码")
    
    args = parser.parse_args()
    
    if args.command == "create":
        create_user(args.username, args.password, args.role, args.quota)
    elif args.command == "delete":
        delete_user(args.username)
    elif args.command == "list":
        list_users()
    elif args.command == "change-password":
        change_password(args.username, args.new_password)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

