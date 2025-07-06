from mcp.server.fastmcp import FastMCP
import requests
import json

# 初始化 MCP 服务
mcp = FastMCP("emadmin_server")

EMADMIN_BASE_URL = "http://fat-emadmin.ppdaicorp.com"

# JWT Token 和 User-Agent 可以也提取为公共变量
EMADMIN_COMMON_HEADERS = {
    "jwt-token": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJsaXpoaW1pbmciLCJ1c2VyX3JvbGUiOiJhZG1pbiIsInVzZXJfbWFpbCI6ImxpemhpbWluZ0BwcGRhaS5jb20iLCJ1c2VyX29yZyI6IuWfuuehgOahhuaetiIsInVzZXJfbmFtZSI6ImxpemhpbWluZyIsImlzcyI6InBhdXRoIiwiZXhwIjoxODgwMDEwNTMzLCJpYXQiOjE1NjQzOTEzMzMsImp0aSI6ImQwYTQ0YjMzLWZhNzItNDQ1Yy1iYTk5LWM1MTQ2NWY2ZDBiNCJ9.wrl2OPgeMz1D3xHViz_2QXV2_KrATJvBVkCUc0qb5E0"
}

# ----------------------------
# 工具函数定义
# ----------------------------


@mcp.tool()
def emadmin_query_dns(domain: str) -> dict:
    """
    查询指定域名的公共 DNS 记录，获取其 IP 地址。

    参数:
        domain (str): 要查询的域名

    返回:
        dict: 包含 'success' 状态和可能的 'ip' 或 'error' 信息。
    """
    url = f"{EMADMIN_BASE_URL}/api/publicdns"
    headers = {
        "Content-Type": "application/json",
        **EMADMIN_COMMON_HEADERS
    }
    params = {
        "domain": domain,
        "page": 1,
        "size": 10
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

        if data.get("code") == 0:
            content = data.get("details", {}).get("content", [])
            if len(content) > 0:
                ip = content[0].get("ip")
                return {"success": True, "ip": ip}
            else:
                return {"success": False, "error": "未找到对应的 DNS 记录"}
        else:
            return {"success": False, "error": data.get("message", "未知错误")}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def emadmin_create_public_dns(domain: str) -> dict:
    """
    创建公共 DNS 的接口调用。

    参数:
        domain (str): 要创建的域名

    返回:
        dict: 包含 success 状态和可能的错误信息或 env_id
    """
    url = f"{EMADMIN_BASE_URL}/api/publicdns/apply/create"
    headers = {
        "Content-Type": "application/json",
        **EMADMIN_COMMON_HEADERS
    }

    # 构建请求体
    req_data = {
        "domain": domain,
        "type": "CREATE",
    }

    if "ppdaicorp.com" in domain or "ppdapi.com" in domain:
        req_data["dnstype"] = "ip"
        req_data["ip"] = "10.112.18.29"
    else:
        req_data["dnstype"] = "dns"

    try:
        response = requests.post(url, headers=headers, json=req_data)
        response.raise_for_status()
        data = response.json()

        if data.get("code") == "0":
            return {"success": True, "message": data.get("details", "DNS 创建成功")}
        else:
            return {"success": False, "error": data.get("details", "未知错误")}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def emadmin_create_env(name: str, description: str, owner: str) -> dict:
    """
    Call the /api/envs endpoint to create an environment.

    Parameters:
        name (str): The name of the environment.
        description (str): Description of the environment.
        owner (str): Owner of the environment.

    Returns:
        dict: A response containing 'success' status and either the env ID or error message.
    """
    url = f"{EMADMIN_BASE_URL}/api/envs"
    headers = {
        "Referer": EMADMIN_BASE_URL,
        **EMADMIN_COMMON_HEADERS
    }
    payload = {
        "name": name,
        "description": description,
        "longTerm": False,
        "basicApps": ["基础服务-DNS", "基础服务-NGINX"],
        "owner": owner,
        "templateId": None,
        "startApps": [],
        "sourceEnv": None,
        "enableMesh": True,
        "timeZone": None,
        "forbidCrossNg": True,
        "forbidLocalNg": False
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        if data.get("code") == 0:
            return {"success": True, "env_id": data["details"]}
        else:
            return {"success": False, "error": data.get("message", "未知错误")}
    except Exception as e:
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    mcp.run(transport="stdio")
