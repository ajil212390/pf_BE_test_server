import urllib.request
import urllib.error

for u in range(1, 10):
    try:
        req = urllib.request.urlopen(f'http://localhost:8000/api/supplier/{u}/dashboard/')
        print(f'{u}: {req.read().decode("utf-8")}')
    except urllib.error.HTTPError as e:
        print(f'{u}: {e.code} {e.read().decode("utf-8")}')
