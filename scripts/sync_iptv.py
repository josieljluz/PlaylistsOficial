import requests

print("🔄 Baixando lista IPTV...")

url = "https://iptv-org.github.io/iptv/index.m3u"
r = requests.get(url)

with open("playlist.m3u", "w", encoding="utf-8") as f:
    f.write(r.text)

print("✅ Atualização concluída!")
