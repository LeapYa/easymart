# 🛒 EasyMart 在线商城系统

一个基于 **FastAPI + SQLite + Jinja2** 构建的简易在线商城系统，专为**软件测试实训**设计。

系统涵盖用户管理、商品管理、购物车与订单管理三大核心模块，预置了多种角色账号和丰富的商品数据，可直接用于功能测试、安全测试、边界值测试等实训练习。

---

## 🚀 快速启动

### 环境要求

- Python 3.10+

### 一键安装 & 运行

```bash
pip install fastapi uvicorn jinja2 aiosqlite
python app.py
```

启动后访问：[http://localhost:8000](http://localhost:8000)

---

## 👤 预置账号

| 角色   | 用户名   | 密码         | 权限说明                     |
|--------|----------|--------------|------------------------------|
| 管理员 | `admin`  | `admin123`   | 用户管理 + 商品管理 + 全部订单 |
| 卖家   | `seller` | `seller123`  | 商品管理 + 全部订单           |
| 买家   | `buyer`  | `buyer123`   | 浏览商品 + 购物车 + 下单      |

---

## 📦 功能模块

### 模块一：用户模块
- 注册（用户名 / 密码 / 确认密码 / 邮箱 / 手机号）
- 登录 / 登出
- 修改密码（需验证原密码）
- 查看 / 编辑个人信息
- 三种角色：`buyer` / `seller` / `admin`

### 模块二：商品模块
- 商品列表（分页，每页 10 条）
- 搜索（名称模糊 + 分类筛选 + 价格区间）
- 商品详情页
- 卖家：添加 / 编辑 / 上下架 / 删除商品

### 模块三：订单模块
- 购物车：添加 / 修改数量 / 删除 / 清空
- 下单结算（库存不足禁止、空购物车禁止）
- 订单列表（按状态筛选）
- 取消订单 / 卖家修改订单状态
- 管理员：用户管理（查看列表 / 删除 / 修改角色）

---

## 🏗️ 技术架构

```
easymart/
├── app.py              # 主应用（路由 + 数据库初始化 + 业务逻辑）
├── templates/          # Jinja2 模板目录
│   ├── base.html       # 基础布局模板（导航栏 + 全局样式）
│   ├── login.html      # 登录页（分屏布局）
│   ├── register.html   # 注册页（分屏布局）
│   ├── profile.html    # 个人中心
│   ├── products.html   # 商品列表
│   ├── product_detail.html  # 商品详情
│   ├── product_form.html    # 商品添加/编辑表单
│   ├── product_manage.html  # 卖家商品管理
│   ├── cart.html       # 购物车
│   ├── orders.html     # 订单列表
│   └── user_manage.html     # 管理员用户管理
├── easymart.db         # SQLite 数据库（自动生成）
└── README.md
```

---

## 🧪 实训用途说明

本系统在代码中**刻意埋藏了 32 个缺陷（Bug）**，涵盖安全漏洞、逻辑错误、前端交互缺陷等多种类型，旨在模拟真实开发场景中"不经意间"遗留的问题，供在实训中通过**黑盒测试、白盒测试、安全测试**等手段进行发现和验证。

> ⚠️ **注意**：所有缺陷均未在代码中做任何注释标记，需要测试者自行发现。

<details>
<summary>📋 点击展开：32 个预埋缺陷完整清单</summary>

### 🔐 安全类缺陷（Security）

| 编号 | 缺陷描述 | 所在位置 | 缺陷类型 |
|------|----------|----------|----------|
| 1 | 密码以明文存储在数据库中，未做任何哈希处理 | `app.py` 注册 / 登录逻辑 | 安全漏洞 |
| 2 | Session 密钥硬编码在源码中（`easymart-super-secret-key-for-testing-only`） | `app.py` 第 17 行 | 安全漏洞 |
| 3 | 商品搜索存在 SQL 注入漏洞（搜索关键词直接拼接 SQL） | `app.py` `products_list` 路由，第 351 行 | 安全漏洞 |
| 4 | 分类筛选存在 SQL 注入漏洞（分类参数直接拼接 SQL） | `app.py` `products_list` 路由，第 353 行 | 安全漏洞 |
| 5 | 价格区间筛选存在 SQL 注入风险（float 转换后直接拼接） | `app.py` `products_list` 路由，第 357/362 行 | 安全漏洞 |
| 6 | 错误信息中泄露完整的数据库异常堆栈（`detail=f"Database query failed: {str(e)}"`) | `app.py` 第 375 行 | 信息泄露 |

### 🔒 权限与鉴权类缺陷（Authorization）

| 编号 | 缺陷描述 | 所在位置 | 缺陷类型 |
|------|----------|----------|----------|
| 7 | 卖家商品管理页面未校验角色，任何登录用户（含 buyer）都可访问 | `app.py` `seller_products` 路由 | 越权访问 |
| 8 | 添加商品接口未校验卖家角色，买家也可以添加商品 | `app.py` `add_product` 路由 | 越权访问 |
| 9 | 编辑商品接口未校验卖家角色 | `app.py` `edit_product` 路由 | 越权访问 |
| 10 | 商品上下架接口未校验卖家角色 | `app.py` `toggle_product_status` 路由 | 越权访问 |
| 11 | 删除商品接口未校验卖家角色 | `app.py` `delete_product` 路由 | 越权访问 |
| 12 | 管理员用户管理页面未校验 admin 角色，任何登录用户可访问 | `app.py` `list_users` 路由 | 越权访问 |
| 13 | 删除用户接口未校验 admin 角色 | `app.py` `delete_user` 路由 | 越权访问 |
| 14 | 修改用户角色接口未校验 admin 角色 | `app.py` `update_user_role` 路由 | 越权访问 |
| 15 | 订单状态修改接口未校验 seller/admin 角色，任何用户可修改 | `app.py` `update_order_status` 路由 | 越权访问 |

### ⚙️ 业务逻辑类缺陷（Logic）

| 编号 | 缺陷描述 | 所在位置 | 缺陷类型 |
|------|----------|----------|----------|
| 16 | 注册时缺少密码长度校验（6-16 位），只校验了字符类型 | `app.py` `register_user`，第 191 行 | 校验缺失 |
| 17 | 注册时缺少"密码与确认密码一致性"校验 | `app.py` `register_user`，第 191-198 行 | 校验缺失 |
| 18 | 修改密码时未验证"原密码"是否正确，直接允许修改 | `app.py` `change_password`，第 304-313 行 | 逻辑漏洞 |
| 19 | 分页计算使用整除（`//`）导致最后一页商品丢失（如 21 条商品只显示 2 页） | `app.py` 第 377 行 | 逻辑错误 |
| 20 | 商品详情页：下架商品的库存被设为 -1 而非提示"已下架" | `app.py` `product_detail`，第 419 行 | 逻辑错误 |
| 21 | 下单时引用了未定义的变量 `now_str`，会导致 500 错误 | `app.py` `checkout`，第 775 行 | 运行时错误 |
| 22 | 下单后未扣减商品库存 | `app.py` `checkout`，第 782-788 行 | 逻辑缺失 |
| 23 | 取消订单后未恢复商品库存 | `app.py` `cancel_order`，第 886-889 行 | 逻辑缺失 |
| 24 | 删除商品时未检查是否有关联订单，直接物理删除 | `app.py` `delete_product`，第 622-623 行 | 数据完整性 |
| 25 | 购物车数量修改未做下限校验，可以设为 0 或负数 | `app.py` `update_cart_quantity`，第 701 行 | 边界缺失 |
| 26 | 加入购物车时未检查商品是否已下架 | `app.py` `add_to_cart`，第 671-685 行 | 校验缺失 |
| 27 | 订单详情中如果关联商品被删除，访问会触发 TypeError 崩溃 | `app.py` `view_orders`，第 845-846 行 | 运行时错误 |
| 28 | 管理员可以删除自己的账号，导致系统无法管理 | `app.py` `delete_user`，第 948-949 行 | 逻辑漏洞 |
| 29 | 修改角色接口未校验角色值合法性，可传入任意字符串 | `app.py` `update_user_role`，第 965 行 | 校验缺失 |
| 30 | 订单状态修改未校验状态流转合法性（如可以从"已完成"改回"待付款"） | `app.py` `update_order_status`，第 911 行 | 逻辑漏洞 |

### 🖥️ 前端与交互类缺陷（Frontend）

| 编号 | 缺陷描述 | 所在位置 | 缺陷类型 |
|------|----------|----------|----------|
| 31 | 注册页面"确认密码"字段使用 `type="text"` 而非 `type="password"`，密码明文可见 | `register.html` 确认密码输入框 | 前端缺陷 |
| 32 | 购物车页面数量输入框的字体颜色为白色（`color: white`），在白色背景下不可见 | `cart.html` `.cart-qty-input` 样式 | UI 缺陷 |

</details>

---

## 🚢 部署指南

### 方式一：直接部署到云服务器

适用于拥有 Ubuntu / CentOS / Debian 等 Linux 云主机的场景。

```bash
# 1. 克隆项目
git clone https://github.com/你的用户名/easymart.git
cd easymart

# 2. 创建虚拟环境并安装依赖
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. 后台启动服务（监听公网，可选传入备案号）
# 如果不需要显示备案号，直接运行即可（不传 ICP_BEIAN 环境变量则不显示）
export ICP_BEIAN="京ICP备XXXXXXXX号-X"
nohup uvicorn app:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &
```

启动后通过 `http://你的服务器IP:8000` 访问。

> 💡 **公网演示/实训环境部署建议**：搭配 Nginx 反向代理，将 80/443 端口转发到 8000 端口，并配置 SSL 证书。

### 方式二：Docker 部署（推荐）

适用于 Docker 环境，一键构建并运行。

```bash
# 1. 克隆项目
git clone https://github.com/你的用户名/easymart.git
cd easymart

# 2. 使用 Docker Compose 一键启动（可选传入备案号）
# 若不需要备案号，可直接运行：docker compose up -d
ICP_BEIAN="京ICP备XXXXXXXX号-X" docker compose up -d

# 3. 查看运行状态
docker compose ps
```

或者手动构建：

```bash
# 构建镜像
docker build -t easymart .

# 运行容器（可选传入备案号）
docker run -d -p 8000:8000 --name easymart -e ICP_BEIAN="京ICP备XXXXXXXX号-X" easymart
```

### 方式三：Nginx 反向代理配置参考

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 📄 License

本项目基于 [MIT License](./LICENSE) 开源，详情请参阅 `LICENSE` 文件。

> ⚠️ **声明**：本项目仅用于教学实训目的，系统中刻意预埋了安全漏洞与逻辑缺陷，**严禁用于生产环境**。
