import json, urllib.request
body = json.dumps({'supplierusername':'demo','supplieruserpassword':'demo'}).encode()
req = urllib.request.Request('http://127.0.0.1:8000/api/login-supplier/', data=body, headers={'Content-Type':'application/json'})
try:
    with urllib.request.urlopen(req) as r:
        print(r.status)
        print(r.read().decode())
except Exception as e:
    print(type(e).__name__, e)
