import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# 数据库连接配置
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./transai.db")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set")

engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# 创建默认admin用户的函数
def create_default_admin():
    """创建默认的admin用户"""
    from .models import User, UserRole
    from .auth import get_password_hash
    
    db = SessionLocal()
    try:
        # 检查admin用户是否已存在
        admin_user = db.query(User).filter(User.username == 'admin').first()
        if not admin_user:
            # 创建admin用户
            hashed_password = get_password_hash('admin123')
            admin_user = User(
                username='admin',
                password=hashed_password,
                role=UserRole.admin,
                quota=100000,
                status=True
            )
            db.add(admin_user)
            db.commit()
            print("Default admin user created successfully")
            print("Username: admin")
            print("Password: admin123")
        else:
            print("Admin user already exists")
    except Exception as e:
        print(f"Error creating admin user: {e}")
        db.rollback()
    finally:
        db.close()

# 在应用启动时创建默认admin用户
def init_db():
    """初始化数据库"""
    Base.metadata.create_all(bind=engine)
    create_default_admin()

# Dependency to get a DB session
def get_db():
    print("--- DB: Creating new session ---")
    db = SessionLocal()
    try:
        yield db
    finally:
        print("--- DB: Closing session ---")
        db.close()
