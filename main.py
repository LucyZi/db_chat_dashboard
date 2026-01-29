# main.py
import os
import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

# ==============================================================================
# --- 1. 配置区域：请在此处修改您的看板信息 ---
# ==============================================================================
# 您的 Databricks 工作区 URL
DATABRICKS_INSTANCE_URL = "https://dbc-6ef01cae-d1e4.cloud.databricks.com" 
# 您想要嵌入的看板 ID
DASHBOARD_ID = "01f0fb8c6b2d1ae4a3e9ebafefa9dc31"

# ==============================================================================
# --- 2. 安全区域：从环境变量中读取机密信息 ---
# ==============================================================================
# 这些值将在 Render 的环境中设置
DATABRICKS_HOST = os.getenv("DATABRICKS_HOST", DATABRICKS_INSTANCE_URL) # 默认为上面的 URL
CLIENT_ID = os.getenv("DATABRICKS_CLIENT_ID")
CLIENT_SECRET = os.getenv("DATABRICKS_CLIENT_SECRET")

# ==============================================================================
# --- 3. 前端模板：将 HTML 和 JavaScript 作为 Python 字符串 ---
# ==============================================================================
# 我们使用一个普通的字符串模板和 .format() 方法，以避免 f-string 和 JavaScript 语法冲突
HTML_TEMPLATE_STRING = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Databricks Dashboard</title>
    <style>
        body, html {{ margin: 0; padding: 0; height: 100%; }}
        #dashboard-container {{ width: 100%; height: 100vh; }}
        .loading {{ display: flex; justify-content: center; align-items: center; height: 100%; font-family: sans-serif; color: #888; }}
    </style>
</head>
<body>
    <div id="dashboard-container">
        <div class="loading">Loading Secure Dashboard...</div>
    </div>

    <script type="module">
        import {{ DatabricksDashboard }} from "https://cdn.jsdelivr.net/npm/@databricks/aibi-client@0.9.0/dist/databricks-aibi-client.esm.js";

        async function embedDashboard() {{
            try {{
                const response = await fetch('/api/get-token');
                if (!response.ok) {{
                    const errorText = await response.text();
                    throw new Error(`Failed to get token: ${{response.status}} ${{response.statusText}}. Server says: ${{errorText}}`);
                }}
                const tokenData = await response.json();
                const accessToken = tokenData.access_token;

                const dashboard = new DatabricksDashboard({{
                    instanceUrl: "{DATABRICKS_INSTANCE_URL}",
                    dashboardId: "{DASHBOARD_ID}",
                    token: accessToken,
                    container: document.getElementById("dashboard-container"),
                }});

                await dashboard.initialize();
                
            }} catch (error) {{
                console.error("Error embedding dashboard:", error);
                document.querySelector('.loading').innerText = `Failed to load dashboard. Please check the browser console for details.`;
            }}
        }}

        embedDashboard();
    </script>
</body>
</html>
"""

# 使用 .format() 方法安全地将配置值插入到模板中
HTML_TEMPLATE = HTML_TEMPLATE_STRING.format(
    DATABRICKS_INSTANCE_URL=DATABRICKS_INSTANCE_URL,
    DASHBOARD_ID=DASHBOARD_ID
)


# ==============================================================================
# --- 4. 后端逻辑：FastAPI 应用 ---
# ==============================================================================
app = FastAPI()

@app.get("/api/get-token")
def get_databricks_token():
    """
    使用服务主体凭证，从 Databricks 获取一个临时的 OAuth 访问令牌。
    """
    if not all([DATABRICKS_HOST, CLIENT_ID, CLIENT_SECRET]):
        raise HTTPException(status_code=500, detail="服务器环境变量未正确配置。管理员需要设置 DATABRICKS_HOST, DATABRICKS_CLIENT_ID, 和 DATABRICKS_CLIENT_SECRET。")

    auth_url = f"{{DATABRICKS_HOST}}/oauth2/token"
    
    try:
        response = requests.post(
            auth_url,
            auth=(CLIENT_ID, CLIENT_SECRET),
            data={{"grant_type": "client_credentials"}}
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"获取 Databricks 令牌失败: {e}")
        # 在生产环境中，更详细地记录错误会很有帮助
        if e.response is not None:
            print(f"响应状态码: {e.response.status_code}")
            print(f"响应内容: {e.response.text}")
        raise HTTPException(status_code=502, detail="无法从 Databricks 获取访问令牌。可能是凭证错误或网络问题。")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """
    当用户访问根 URL 时，直接返回上面定义的 HTML 页面。
    """
    return HTML_TEMPLATE
