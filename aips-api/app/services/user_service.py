import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, List
from uuid import uuid4

from app.core.config import TASKS_DIR
from app.schemas.auth import UserCreate, UserResponse


class User:
    def __init__(self, id: str, username: str, email: str, password_hash: str, created_at: datetime, is_active: bool = True):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.created_at = created_at
        self.is_active = is_active

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "password_hash": self.password_hash,
            "created_at": self.created_at.isoformat(),
            "is_active": self.is_active
        }

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        return cls(
            id=data["id"],
            username=data["username"],
            email=data["email"],
            password_hash=data["password_hash"],
            created_at=datetime.fromisoformat(data["created_at"]),
            is_active=data.get("is_active", True)
        )

    def to_response(self) -> UserResponse:
        return UserResponse(
            id=self.id,
            username=self.username,
            email=self.email,
            created_at=self.created_at,
            is_active=self.is_active
        )


class UserService:
    def __init__(self, users_dir: Path = None):
        self.users_dir = users_dir or TASKS_DIR / "users"
        self.users_dir.mkdir(parents=True, exist_ok=True)
        self.users_file = self.users_dir / "users.json"
        self._users: dict[str, User] = {}
        self._load_users()

    def _load_users(self):
        """从文件加载用户数据"""
        if self.users_file.exists():
            try:
                with open(self.users_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for user_data in data:
                        user = User.from_dict(user_data)
                        self._users[user.id] = user
            except Exception:
                pass

    def _save_users(self):
        """保存用户数据到文件"""
        try:
            data = [user.to_dict() for user in self._users.values()]
            with open(self.users_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _hash_password(self, password: str) -> str:
        """密码哈希"""
        return hashlib.sha256(password.encode()).hexdigest()

    def create_user(self, user_data: UserCreate) -> User:
        """创建新用户"""
        # 检查用户名是否已存在
        if self.get_user_by_username(user_data.username):
            raise ValueError("用户名已存在")
        
        # 检查邮箱是否已存在
        if self.get_user_by_email(user_data.email):
            raise ValueError("邮箱已被注册")
        
        # 创建新用户
        user_id = uuid4().hex
        password_hash = self._hash_password(user_data.password)
        user = User(
            id=user_id,
            username=user_data.username,
            email=user_data.email,
            password_hash=password_hash,
            created_at=datetime.now()
        )
        
        self._users[user_id] = user
        self._save_users()
        
        return user

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """根据ID获取用户"""
        return self._users.get(user_id)

    def get_user_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        for user in self._users.values():
            if user.username == username:
                return user
        return None

    def get_user_by_email(self, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        for user in self._users.values():
            if user.email == email:
                return user
        return None

    def verify_password(self, username: str, password: str) -> Optional[User]:
        """验证用户密码"""
        user = self.get_user_by_username(username)
        if user and user.password_hash == self._hash_password(password):
            return user
        return None

    def change_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        """修改密码"""
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        
        if user.password_hash != self._hash_password(old_password):
            return False
        
        user.password_hash = self._hash_password(new_password)
        self._save_users()
        return True

    def delete_user(self, user_id: str) -> bool:
        """删除用户"""
        if user_id in self._users:
            del self._users[user_id]
            self._save_users()
            return True
        return False

    def list_users(self) -> List[User]:
        """获取所有用户"""
        return list(self._users.values())


# 创建全局用户服务实例
user_service = UserService()
