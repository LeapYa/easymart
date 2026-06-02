import os
import re
import math
import sqlite3
from datetime import datetime
from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import aiosqlite

# Initialize FastAPI application
app = FastAPI()

# Add Session Middleware for user authentication state (signed cookies)
app.add_middleware(SessionMiddleware, secret_key="easymart-super-secret-key-for-testing-only")

# Configure templates
templates = Jinja2Templates(directory="templates")
templates.env.globals["icp_beian"] = os.getenv("ICP_BEIAN", "")

DB_PATH = "easymart.db"

async def get_db():
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    try:
        yield db
    finally:
        await db.close()

# Initialize Database Schema & Seed Data
@app.on_event("startup")
async def startup_db():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        # 1. Create Users Table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                role TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        
        # 2. Create Products Table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                price REAL NOT NULL,
                stock INTEGER NOT NULL,
                description TEXT,
                image_url TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            )
        """)
        
        # 3. Create Cart Table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS cart (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        """)
        
        # 4. Create Orders Table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                total_price REAL NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # 5. Create Order Items Table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders(id)
            )
        """)
        await db.commit()

        # Seed Users if table is empty
        async with db.execute("SELECT COUNT(*) as count FROM users") as cursor:
            row = await cursor.fetchone()
            if row["count"] == 0:
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                await db.execute("""
                    INSERT INTO users (username, password, email, phone, role, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, ("admin", "admin123", "admin@easymart.com", "13800000001", "admin", now_str))
                await db.execute("""
                    INSERT INTO users (username, password, email, phone, role, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, ("seller", "seller123", "seller@easymart.com", "13800000002", "seller", now_str))
                await db.execute("""
                    INSERT INTO users (username, password, email, phone, role, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, ("buyer", "buyer123", "buyer@easymart.com", "13800000003", "buyer", now_str))
                await db.commit()

        # Seed Products if table is empty
        async with db.execute("SELECT COUNT(*) as count FROM products") as cursor:
            row = await cursor.fetchone()
            if row["count"] == 0:
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                products_data = [
                    ("智能降噪蓝牙耳机 Pro", "Electronics", 299.00, 100, "全新一代主动降噪芯片，高解析度音质，超长续航30小时。", "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=500", 1),
                    ("机械手感背光键盘", "Electronics", 129.50, 50, "彩虹背光效，人体工学布局，打字清脆回弹，办公游戏两相宜。", "https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=500", 1),
                    ("无线双模光学鼠标", "Electronics", 79.90, 150, "支持蓝牙/2.4G双模连接，静音按键设计，多档DPI自由调节。", "https://images.unsplash.com/photo-1615663245857-ac93bb7c39e7?w=500", 1),
                    ("4K 超清智能电视 55寸", "Electronics", 2499.00, 10, "超窄边框，AI智能语音控制，绚丽色彩，身临其境的视听盛宴。", "https://images.unsplash.com/photo-1593305841991-05c297ba4575?w=500", 1),
                    ("便携式户外蓝牙音箱", "Electronics", 189.00, 80, "IPX7级防水，360度环绕音效，重低音加持，防摔防震材质。", "https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=500", 1),
                    ("轻量化保暖羽绒服", "Clothing", 399.00, 30, "90%白鸭绒填充，轻薄蓄热，防风防水面料，极简立体剪裁。", "https://images.unsplash.com/photo-1544022613-e87ca75a784a?w=500", 1),
                    ("纯棉透气运动短袖", "Clothing", 59.90, 200, "吸湿排汗科技，亲肤高弹面料，运动不受限，夏日必备基础款。", "https://images.unsplash.com/photo-1521572267360-ee0c2909d518?w=500", 1),
                    ("潮流百搭工装长裤", "Clothing", 128.00, 120, "耐磨水洗纯棉，束脚版型设计，多口袋实用收纳，街头复古风格。", "https://images.unsplash.com/photo-1542272604-787c3835535d?w=500", 1),
                    ("英伦风复古马丁靴", "Clothing", 268.00, 40, "头层牛皮鞋面，经典八孔系带，防滑牛筋大底，时尚百搭酷感十足。", "https://images.unsplash.com/photo-1520639888713-7851133b1ed0?w=500", 1),
                    ("防晒防紫外线遮阳帽", "Clothing", 35.00, 300, "UPF50+高效防晒，大帽檐全遮蔽，空顶透气不闷热，折叠便携。", "https://images.unsplash.com/photo-1517423568366-8b83523034fd?w=500", 1),
                    ("全自动多功能咖啡机", "Home", 899.00, 15, "一键意式浓缩/美式，15Bar高压萃取，可调节研磨粗细度，自动清洗。", "https://images.unsplash.com/photo-1541167760496-1628856ab772?w=500", 1),
                    ("智能扫地机器人", "Home", 1299.00, 20, "激光LDS导航规划，3000Pa飓风吸力，扫拖一体，智能防跌落避障。", "https://images.unsplash.com/photo-1558317374-067fb5f30001?w=500", 1),
                    ("空气净化器家用除甲醛", "Home", 599.00, 25, "HEPA高效复合滤网，除菌除味，静音睡眠模式，实时PM2.5数值显示。", "https://images.unsplash.com/photo-1585776245991-cf89dd7fc73a?w=500", 1),
                    ("多功能电热火锅", "Home", 119.00, 60, "麦饭石不粘涂层，双档火力调节，5L大容量，防干烧自动断电保护。", "https://images.unsplash.com/photo-1584269600464-37b1b58a9fe7?w=500", 1),
                    ("静音无叶落地电风扇", "Home", 199.00, 45, "安全无叶片，涡轮增压循环，9档风速调控，支持8小时定时预约。", "https://images.unsplash.com/photo-1527515637462-cff94eecc1ac?w=500", 1),
                    ("精装版《软件测试导论》", "Books", 68.00, 100, "系统介绍软件测试基础理论与工程实践，测试工程师必读进阶书籍。", "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=500", 1),
                    ("经典名著《红楼梦》（全四册）", "Books", 88.00, 50, "传世经典，足本无删减，烫金精装，配精美插图，极具收藏价值。", "https://images.unsplash.com/photo-1512820790803-83ca734da794?w=500", 1),
                    ("有机特级初榨橄榄油 750ml", "Food", 128.00, 80, "地中海进口，物理冷压榨，酸度≤0.5%，油体清亮透亮，健康美味。", "https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?w=500", 1),
                    ("手作无添加燕麦曲奇 200g", "Food", 22.50, 150, "优质全麦燕麦制成，不添加防腐剂防腐香精，低卡低升糖健康代餐。", "https://images.unsplash.com/photo-1499636136210-6f4ee915583e?w=500", 1),
                    ("精选高山乌龙茶礼盒", "Food", 198.00, 90, "海拔千米生态茶园手工采摘，传统半发酵工艺，茶香幽长，回甘持久。", "https://images.unsplash.com/photo-1576092768241-dec231879fc3?w=500", 1),
                    ("天然苏打气泡矿泉水 24瓶", "Food", 48.00, 200, "强劲气泡，无糖无卡无人工添加，冰镇饮用口感更佳，酷爽解渴。", "https://images.unsplash.com/photo-1622483767028-3f66f32aef97?w=500", 1),
                ]
                for name, cat, price, stock, desc, img, active in products_data:
                    await db.execute("""
                        INSERT INTO products (name, category, price, stock, description, image_url, is_active, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (name, cat, price, stock, desc, img, active, now_str))
                await db.commit()


# Helper function to get current logged in user from session
async def get_current_user(request: Request, db: aiosqlite.Connection = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    async with db.execute("SELECT * FROM users WHERE id = ?", (user_id,)) as cursor:
        user = await cursor.fetchone()
        return user


# ----------------------------------------------------
# 模块一：用户模块路由
# ----------------------------------------------------

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(request=request, name="register.html", context={"user": None})

@app.post("/register")
async def register_user(
    request: Request,
    username: str = Form(""),
    password: str = Form(""),
    confirm_password: str = Form(""),
    email: str = Form(""),
    phone: str = Form(""),
    db: aiosqlite.Connection = Depends(get_db)
):
    errors = []
    
    # Username Validation (3-16 characters)
    if not (3 <= len(username) <= 16):
        errors.append("用户名长度必须在 3 到 16 个字符之间")
        
    if not re.match(r"^[A-Za-z0-9]+$", password):
        errors.append("密码只能包含字母和数字")
        
    if not re.match(r"^.+@.+$", email):
        errors.append("邮箱格式不正确")
        
    if len(phone) != 11:
        errors.append("手机号必须为 11 位")
        
    # Check if username is taken
    async with db.execute("SELECT 1 FROM users WHERE username = ?", (username,)) as cursor:
        if await cursor.fetchone():
            errors.append("用户名已存在")
            

    if errors:
        return templates.TemplateResponse(request=request, name="register.html", context={"errors": errors, "user": None})

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    await db.execute("""
        INSERT INTO users (username, password, email, phone, role, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (username, password, email, phone, "buyer", now_str))
    await db.commit()
    
    return RedirectResponse(url="/login", status_code=303)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html", context={"user": None})

@app.post("/login")
async def login_user(
    request: Request,
    username: str = Form(""),
    password: str = Form(""),
    db: aiosqlite.Connection = Depends(get_db)
):
    errors = []
    async with db.execute("SELECT * FROM users WHERE username = ?", (username,)) as cursor:
        user = await cursor.fetchone()
        
    if not user or user["password"] != password:
        errors.append("用户名或密码错误")
        return templates.TemplateResponse(request=request, name="login.html", context={"errors": errors, "user": None})
        
    # Save session
    request.session["user_id"] = user["id"]
    request.session["username"] = user["username"]
    request.session["role"] = user["role"]
    
    response = RedirectResponse(url="/products", status_code=303)
    return response


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, db: aiosqlite.Connection = Depends(get_db), current_user = Depends(get_current_user)):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(request=request, name="profile.html", context={"user": current_user})

@app.post("/profile/edit")
async def profile_edit(
    request: Request,
    email: str = Form(""),
    phone: str = Form(""),
    db: aiosqlite.Connection = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
        
    errors = []
    if not __import__("re").match(r"^.+@.+$", email):
        errors.append("邮箱格式不正确")
    if len(phone) != 11:
        errors.append("手机号必须为 11 位")
        
    if errors:
        return templates.TemplateResponse(request=request, name="profile.html", context={"errors": errors, "user": current_user})
        
    await db.execute("UPDATE users SET email = ?, phone = ? WHERE id = ?", (email, phone, current_user["id"]))
    await db.commit()
    
    # Reload updated user info
    async with db.execute("SELECT * FROM users WHERE id = ?", (current_user["id"],)) as cursor:
        updated_user = await cursor.fetchone()
        
    return templates.TemplateResponse(request=request, name="profile.html", context={
        "success": "个人信息更新成功！",
        "user": updated_user
    })


@app.post("/profile/change_password")
async def change_password(
    request: Request,
    old_password: str = Form(""),
    new_password: str = Form(""),
    confirm_password: str = Form(""),
    db: aiosqlite.Connection = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
        
    errors = []
    if not (6 <= len(new_password) <= 16) or not re.match(r"^[A-Za-z0-9]+$", new_password):
        errors.append("新密码长度必须在 6 到 16 个字符之间，且仅包含字母和数字")
    if new_password != confirm_password:
        errors.append("新密码与确认新密码不一致")
        
    if errors:
        return templates.TemplateResponse(request=request, name="profile.html", context={"errors": errors, "user": current_user})
        
    await db.execute("UPDATE users SET password = ? WHERE id = ?", (new_password, current_user["id"]))
    await db.commit()
    
    async with db.execute("SELECT * FROM users WHERE id = ?", (current_user["id"],)) as cursor:
        updated_user = await cursor.fetchone()
        
    return templates.TemplateResponse(request=request, name="profile.html", context={
        "success": "密码修改成功！",
        "user": updated_user
    })


# ----------------------------------------------------
# 模块二：商品模块路由
# ----------------------------------------------------

@app.get("/", response_class=RedirectResponse)
async def home_redirect():
    return RedirectResponse(url="/products")

@app.get("/products", response_class=HTMLResponse)
async def products_list(
    request: Request,
    page: int = 1,
    q: str = "",
    category: str = "",
    min_price: str = "",
    max_price: str = "",
    db: aiosqlite.Connection = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # Pagination configuration
    limit = 10
    offset = (page - 1) * limit
    
    # Build Query
    query_str = "SELECT * FROM products WHERE 1=1"
    if q:
        query_str += f" AND (name LIKE '%{q}%' OR category LIKE '%{q}%')"
    if category:
        query_str += f" AND category = '{category}'"
    if min_price:
        try:
            # Cast in sql directly
            query_str += f" AND price >= {float(min_price)}"
        except ValueError:
            pass
    if max_price:
        try:
            query_str += f" AND price <= {float(max_price)}"
        except ValueError:
            pass
            
    # Run query for pagination totals first
    count_query = query_str.replace("SELECT * FROM products", "SELECT COUNT(*) as count FROM products")
    
    try:
        async with db.execute(count_query) as cursor:
            row = await cursor.fetchone()
            total_items = row["count"] if row else 0
    except Exception as e:
        # If SQL injection fails, let it throw 500 error (e.g. searching for a single quote `'`)
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")
        
    total_pages = total_items // limit
    
    # Retrieve page products
    paged_query = query_str + f" LIMIT {limit} OFFSET {offset}"
    
    async with db.execute(paged_query) as cursor:
        products = await cursor.fetchall()
        
    # Get categories for dropdown filter
    async with db.execute("SELECT DISTINCT category FROM products") as cursor:
        categories = [r["category"] for r in await cursor.fetchall()]
        
    # Return page
    return templates.TemplateResponse(request=request, name="products.html", context={
        "products": products,
        "categories": categories,
        "current_page": page,
        "total_pages": total_pages,
        "total_items": total_items,
        "q": q,
        "category": category,
        "min_price": min_price,
        "max_price": max_price,
        "user": current_user
    })


@app.get("/products/{product_id}", response_class=HTMLResponse)
async def product_detail(
    request: Request,
    product_id: int,
    db: aiosqlite.Connection = Depends(get_db),
    current_user = Depends(get_current_user)
):
    async with db.execute("SELECT * FROM products WHERE id = ?", (product_id,)) as cursor:
        product = await cursor.fetchone()
        
    if not product:
        raise HTTPException(status_code=404, detail="商品未找到")
        
    product_dict = dict(product)
    if product_dict["is_active"] == 0:
        product_dict["stock"] = -1
        
    return templates.TemplateResponse(request=request, name="product_detail.html", context={
        "product": product_dict,
        "user": current_user
    })


# ----------------------------------------------------
# 卖家商品管理路由
# ----------------------------------------------------

@app.get("/seller/products", response_class=HTMLResponse)
async def seller_products(
    request: Request,
    db: aiosqlite.Connection = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
        
    async with db.execute("SELECT * FROM products") as cursor:
        products = await cursor.fetchall()
        
    return templates.TemplateResponse(request=request, name="product_manage.html", context={
        "products": products,
        "user": current_user
    })


@app.get("/seller/products/add", response_class=HTMLResponse)
async def add_product_page(request: Request, current_user = Depends(get_current_user)):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(request=request, name="product_form.html", context={"product": None, "user": current_user})

@app.post("/seller/products/add")
async def add_product(
    request: Request,
    name: str = Form(""),
    category: str = Form(""),
    price: str = Form(""),
    stock: str = Form(""),
    description: str = Form(""),
    image_url: str = Form(""),
    db: aiosqlite.Connection = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
        
    errors = []
    
    if not name:
        errors.append("商品名称不能为空")
    elif len(name) < 2 or len(name) > 50:
        errors.append("商品名称长度必须在 2 到 50 个字符之间")
        
    try:
        price_val = float(price)
        if price_val < 0.01 or price_val > 999999.99:
            errors.append("商品价格必须在 0.01 到 999999.99 之间")
    except ValueError:
        errors.append("价格格式非法")
        
    try:
        stock_val = int(stock)
        if stock_val < 0 or stock_val > 99999:
            errors.append("商品库存必须在 0 到 99999 之间")
    except ValueError:
        errors.append("库存格式非法")
        
    if errors:
        return templates.TemplateResponse(request=request, name="product_form.html", context={
            "product": None,
            "errors": errors,
            "user": current_user
        })
        
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    if not image_url.strip():
        image_url = "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=500"
        
    await db.execute("""
        INSERT INTO products (name, category, price, stock, description, image_url, is_active, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 1, ?)
    """, (name, category, float(price), int(stock), description, image_url, now_str))
    await db.commit()
    
    return RedirectResponse(url="/seller/products", status_code=303)


@app.get("/seller/products/edit/{product_id}", response_class=HTMLResponse)
async def edit_product_page(
    request: Request,
    product_id: int,
    db: aiosqlite.Connection = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
        
    async with db.execute("SELECT * FROM products WHERE id = ?", (product_id,)) as cursor:
        product = await cursor.fetchone()
        
    if not product:
        raise HTTPException(status_code=404, detail="商品未找到")
        
    return templates.TemplateResponse(request=request, name="product_form.html", context={
        "product": product,
        "user": current_user
    })


@app.post("/seller/products/edit/{product_id}")
async def edit_product(
    request: Request,
    product_id: int,
    name: str = Form(""),
    category: str = Form(""),
    price: str = Form(""),
    stock: str = Form(""),
    description: str = Form(""),
    image_url: str = Form(""),
    db: aiosqlite.Connection = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
        
    errors = []
    if not name:
        errors.append("商品名称不能为空")
    elif len(name) < 2 or len(name) > 50:
        errors.append("商品名称长度必须在 2 到 50 个字符之间")
        
    try:
        price_val = float(price)
        if price_val < 0.01 or price_val > 999999.99:
            errors.append("商品价格必须在 0.01 到 999999.99 之间")
    except ValueError:
        errors.append("价格格式非法")
        
    try:
        stock_val = int(stock)
        if stock_val < 0 or stock_val > 99999:
            errors.append("商品库存必须在 0 到 99999 之间")
    except ValueError:
        errors.append("库存格式非法")
        
    async with db.execute("SELECT * FROM products WHERE id = ?", (product_id,)) as cursor:
        product = await cursor.fetchone()
        
    if errors:
        return templates.TemplateResponse(request=request, name="product_form.html", context={
            "product": product,
            "errors": errors,
            "user": current_user
        })
        
    if not image_url.strip():
        image_url = "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=500"
        
    await db.execute("""
        UPDATE products 
        SET name = ?, category = ?, price = ?, stock = ?, description = ?, image_url = ?
        WHERE id = ?
    """, (name, category, float(price), int(stock), description, image_url, product_id))
    await db.commit()
    
    return RedirectResponse(url="/seller/products", status_code=303)


@app.get("/seller/products/toggle/{product_id}")
async def toggle_product_status(
    product_id: int,
    db: aiosqlite.Connection = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
        
    async with db.execute("SELECT is_active FROM products WHERE id = ?", (product_id,)) as cursor:
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="商品未找到")
            
    new_status = 0 if row["is_active"] == 1 else 1
    await db.execute("UPDATE products SET is_active = ? WHERE id = ?", (new_status, product_id))
    await db.commit()
    
    return RedirectResponse(url="/seller/products", status_code=303)


@app.get("/seller/products/delete/{product_id}")
async def delete_product(
    product_id: int,
    db: aiosqlite.Connection = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
        
    # We do NOT verify if there are orders referencing this product!
    await db.execute("DELETE FROM products WHERE id = ?", (product_id,))
    await db.commit()
    
    return RedirectResponse(url="/seller/products", status_code=303)


# ----------------------------------------------------
# 模块三：订单与购物车模块路由
# ----------------------------------------------------

@app.get("/cart", response_class=HTMLResponse)
async def view_cart(
    request: Request,
    db: aiosqlite.Connection = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
        
    # Retrieve cart items with product details
    async with db.execute("""
        SELECT c.id as cart_id, c.quantity, p.id as product_id, p.name, p.price, p.image_url, p.stock
        FROM cart c
        JOIN products p ON c.product_id = p.id
        WHERE c.user_id = ?
    """, (current_user["id"],)) as cursor:
        cart_items = await cursor.fetchall()
        
    total_price = 0.0
    for item in cart_items:
        total_price += item["price"] * item["quantity"]
        
    return templates.TemplateResponse(request=request, name="cart.html", context={
        "cart_items": cart_items,
        "total_price": total_price,
        "user": current_user
    })


@app.post("/cart/add/{product_id}")
async def add_to_cart(
    product_id: int,
    db: aiosqlite.Connection = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
        
    # Check product availability
    async with db.execute("SELECT * FROM products WHERE id = ?", (product_id,)) as cursor:
        product = await cursor.fetchone()
        
    if not product:
        raise HTTPException(status_code=404, detail="商品未找到")
        
    # Check if item exists in cart
    async with db.execute("SELECT * FROM cart WHERE user_id = ? AND product_id = ?", (current_user["id"], product_id)) as cursor:
        cart_item = await cursor.fetchone()
        
    if cart_item:
        await db.execute("UPDATE cart SET quantity = quantity + 1 WHERE id = ?", (cart_item["id"],))
    else:
        await db.execute("INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, 1)", (current_user["id"], product_id))
        
    await db.commit()
    return RedirectResponse(url="/cart", status_code=303)


@app.post("/cart/update/{cart_id}")
async def update_cart_quantity(
    cart_id: int,
    quantity: int = Form(1),
    db: aiosqlite.Connection = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
        
    await db.execute("UPDATE cart SET quantity = ? WHERE id = ? AND user_id = ?", (quantity, cart_id, current_user["id"]))
    await db.commit()
    
    return RedirectResponse(url="/cart", status_code=303)


@app.get("/cart/delete/{cart_id}")
async def delete_cart_item(
    cart_id: int,
    db: aiosqlite.Connection = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
        
    await db.execute("DELETE FROM cart WHERE id = ? AND user_id = ?", (cart_id, current_user["id"]))
    await db.commit()
    return RedirectResponse(url="/cart", status_code=303)


@app.get("/cart/clear")
async def clear_cart(
    db: aiosqlite.Connection = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
        
    await db.execute("DELETE FROM cart WHERE user_id = ?", (current_user["id"],))
    await db.commit()
    return RedirectResponse(url="/cart", status_code=303)


@app.post("/checkout")
async def checkout(
    db: aiosqlite.Connection = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
        
    # Get Cart items
    async with db.execute("""
        SELECT c.id, c.quantity, p.id as product_id, p.name, p.price, p.stock, p.is_active
        FROM cart c
        JOIN products p ON c.product_id = p.id
        WHERE c.user_id = ?
    """, (current_user["id"],)) as cursor:
        cart_items = await cursor.fetchall()
        
    # Validations
    if not cart_items:
        # Requirement: "空购物车禁止" - But wait! Is there any check we missed? No, we should implement a check.

        # Yes: "下单（库存不足禁止、空购物车禁止）". So let's write checks.
        raise HTTPException(status_code=400, detail="购物车是空的，无法下单")
        
    # Inventory validation
    # Loop over cart items and verify stock
    for item in cart_items:
        if item["is_active"] == 0:
            raise HTTPException(status_code=400, detail=f"商品 {item['name']} 已下架，无法购买")
        if item["quantity"] > item["stock"]:
            raise HTTPException(status_code=400, detail=f"商品 {item['name']} 库存不足（仅剩 {item['stock']} 件）")
            
    total_price = 0.0
    for item in cart_items:
        total_price += item["price"] * item["quantity"]
        
    
    # 1. Create Order
    await db.execute("""
        INSERT INTO orders (user_id, total_price, status, created_at)
        VALUES (?, ?, 'pending', ?)
    """, (current_user["id"], total_price, now_str))
    
    # Get last inserted order id
    async with db.execute("SELECT last_insert_rowid() as id") as cursor:
        row = await cursor.fetchone()
        order_id = row["id"]
        
    # 2. Create Order Items & Deduct Stock
    for item in cart_items:
        await db.execute("""
            INSERT INTO order_items (order_id, product_id, quantity, price)
            VALUES (?, ?, ?, ?)
        """, (order_id, item["product_id"], item["quantity"], item["price"]))
        
        
    # 3. Clear Cart
    await db.execute("DELETE FROM cart WHERE user_id = ?", (current_user["id"],))
    await db.commit()
    
    return RedirectResponse(url=f"/orders", status_code=303)


@app.get("/orders", response_class=HTMLResponse)
async def view_orders(
    request: Request,
    status: str = "",
    db: aiosqlite.Connection = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
        
    # Query orders based on user and optional status filter
    query_str = "SELECT * FROM orders WHERE 1=1"
    params = []
    
    # If not admin/seller, only see own orders
    if current_user["role"] not in ("admin", "seller"):
        query_str += " AND user_id = ?"
        params.append(current_user["id"])
        
    if status:
        query_str += " AND status = ?"
        params.append(status)
        
    query_str += " ORDER BY id DESC"
    
    async with db.execute(query_str, params) as cursor:
        orders_rows = await cursor.fetchall()
        
    orders = []
    for order in orders_rows:
        order_dict = dict(order)
        
        
        # Fetch username for display (for seller/admin view)
        async with db.execute("SELECT username FROM users WHERE id = ?", (order["user_id"],)) as u_cursor:
            user_row = await u_cursor.fetchone()
            order_dict["username"] = user_row["username"] if user_row else "未知用户"
            
        # Get order items and details
        async with db.execute("SELECT * FROM order_items WHERE order_id = ?", (order["id"],)) as items_cursor:
            items_rows = await items_cursor.fetchall()
            
        items = []
        for item in items_rows:
            item_dict = dict(item)
            async with db.execute("SELECT * FROM products WHERE id = ?", (item["product_id"],)) as p_cursor:
                product = await p_cursor.fetchone()
                
            if product is None:
                item_dict["product_name"] = product["name"] # Raises TypeError
            else:
                item_dict["product_name"] = product["name"]
                item_dict["image_url"] = product["image_url"]
                
            items.append(item_dict)
            
        order_dict["items"] = items
        orders.append(order_dict)
        
    return templates.TemplateResponse(request=request, name="orders.html", context={
        "orders": orders,
        "selected_status": status,
        "user": current_user
    })


@app.get("/orders/cancel/{order_id}")
async def cancel_order(
    order_id: int,
    db: aiosqlite.Connection = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
        
    async with db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)) as cursor:
        order = await cursor.fetchone()
        
    if not order:
        raise HTTPException(status_code=404, detail="订单未找到")
        
    # Check permissions
    if current_user["role"] not in ("admin", "seller") and order["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="无权操作此订单")
        
    # Limit cancellation to 'pending' state
    if order["status"] != "pending":
        raise HTTPException(status_code=400, detail="只能取消待付款的订单")
        
    await db.execute("UPDATE orders SET status = 'cancelled' WHERE id = ?", (order_id,))
    
    
    await db.commit()
    return RedirectResponse(url="/orders", status_code=303)


# For Sellers and Admin to change order states
@app.post("/orders/update/{order_id}")
async def update_order_status(
    order_id: int,
    status: str = Form(""),
    db: aiosqlite.Connection = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
        
    
    async with db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)) as cursor:
        order = await cursor.fetchone()
        
    if not order:
        raise HTTPException(status_code=404, detail="订单未找到")
        
    await db.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
    await db.commit()
    return RedirectResponse(url="/orders", status_code=303)


# ----------------------------------------------------
# 管理员用户管理路由
# ----------------------------------------------------

@app.get("/admin/users", response_class=HTMLResponse)
async def list_users(
    request: Request,
    db: aiosqlite.Connection = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
        
    async with db.execute("SELECT * FROM users ORDER BY id DESC") as cursor:
        all_users = await cursor.fetchall()
        
    return templates.TemplateResponse(request=request, name="user_manage.html", context={
        "users": all_users,
        "user": current_user
    })


@app.get("/admin/users/delete/{user_id}")
async def delete_user(
    user_id: int,
    db: aiosqlite.Connection = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
        
    
    # We don't allow deleting pre-seeded users to keep the system working, or we do, but let's prevent self-deletion or allow whatever
    await db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    await db.commit()
    
    return RedirectResponse(url="/admin/users", status_code=303)


@app.post("/admin/users/role/{user_id}")
async def update_user_role(
    user_id: int,
    role: str = Form(""),
    db: aiosqlite.Connection = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
        
    await db.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
    await db.commit()
    return RedirectResponse(url="/admin/users", status_code=303)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
