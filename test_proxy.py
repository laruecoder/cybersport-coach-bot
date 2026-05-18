import urllib.request
import socket

ports = [7890, 10809, 1080, 8080, 10808, 7891, 9090]

print("Testing proxy ports...")
for port in ports:
    try:
        proxy = urllib.request.ProxyHandler({'http': f'http://127.0.0.1:{port}'})
        opener = urllib.request.build_opener(proxy)
        response = opener.open('http://google.com', timeout=3)
        print(f"PORT {port} WORKS!")
    except:
        print(f"Port {port}: failed")

# Also show listening ports
print("\nListening on localhost:")
for port in range(1080, 10910):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', port))
    if result == 0:
        print(f"Port {port}: OPEN")
    sock.close()