# Flask 多租户待办事项管理系统

一个基于 Flask 的全栈 Web 应用，支持用户注册登录、数据隔离与持久化存储。项目从单文件脚本起步，逐步重构为企业级工程化架构，完整展现了从原型到生产环境的演进过程。

## 核心功能

- **安全认证**：基于 Flask-Login 实现注册/登录/退出，密码使用 Werkzeug 哈希存储
- **数据隔离**：User 与 Todo 一对多关联，严格的多租户数据权限控制
- **持久化存储**：SQLite + SQLAlchemy ORM，支持完整的 CRUD 操作
- **防重复提交**：PRG 模式 + location.replace 彻底解决浏览器刷新重放问题
- **云端部署**：完整部署于 PythonAnywhere，支持线上数据无损迁移

## 技术架构演进

| 阶段 | 存储方案 | 架构特点 | 解决的问题 |
|------|---------|---------|-----------|
| V1.0 | JSON 文件 | 单文件脚本 | 快速验证核心业务逻辑 |
| V2.0 | SQLite + SQLAlchemy | 关系型数据库 | 数据结构化、查询性能优化 |
| V3.0 | Flask-Login + 外键约束 | 多租户 SaaS 架构 | 用户隔离、密码安全、权限控制 |

## 本地运行指南

```bash
# 1. 克隆仓库并进入目录
git clone https://github.com/Mark-Kevin77/my-first-flask-app.git
cd my-first-flask-app

# 2. 创建并激活虚拟环境
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux

# 3. 安装依赖并启动
pip install -r requirements.txt
python app.py
```

访问 http://localhost:5000 即可体验。

## 线上演示

- 🔗 **体验地址**：http://markkevin77.pythonanywhere.com
- 👤 **测试账号**：可自行注册新账号体验数据隔离功能

## 项目结构

```text
my-first-flask-app/
├── app.py              # 主应用（路由、模型、模板）
├── requirements.txt    # 依赖清单
├── .gitignore          # Git 忽略规则
└── README.md           # 项目文档