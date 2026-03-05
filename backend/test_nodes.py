import urllib.request
import json

def test_nodes():
    login_req = urllib.request.Request(
        "http://127.0.0.1:8000/api/v1/auth/login",
        data=json.dumps({"email": "test@test.com", "password":"password"}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(login_req) as response:
            token = json.loads(response.read().decode())["access_token"]
        
        req = urllib.request.Request(
            "http://127.0.0.1:8000/api/v1/rag/nodes",
            headers={"Authorization": f"Bearer {token}"}
        )
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            print(f"Nodes: {len(data['nodes'])} Links: {len(data['links'])}")
            if len(data['links']) > 0:
                print("Sample link:", data['links'][0])
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    test_nodes()
