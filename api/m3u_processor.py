"""
Processador de playlists M3U/M3U8 para o IPTV System
Baseado no código original de PlaylistsOficial/m3u_processor.py
"""
import re
import requests
import json
import time
from urllib.parse import urlparse

# Regex para extrair atributos EXTINF
regex_attr = re.compile(r'([\w-]+)="([^"]*)"')

# EPG URLs otimizadas para Brasil e Portugal
EPG_URLS = [
    "https://m3u4u.com/epg/jq2zy9epr3bwxmgwyxr5",
    "https://m3u4u.com/epg/3wk1y24kx7uzdevxygz7",
    "https://m3u4u.com/epg/782dyqdrqkh1xegen4zp",
    "https://www.open-epg.com/files/brazil1.xml.gz",
    "https://www.open-epg.com/files/brazil2.xml.gz",
    "https://www.open-epg.com/files/brazil3.xml.gz",
    "https://www.open-epg.com/files/brazil4.xml.gz",
    "https://www.open-epg.com/files/portugal1.xml.gz",
    "https://www.open-epg.com/files/portugal2.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_BR1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_PT1.xml.gz",
    "https://raw.githubusercontent.com/josieljefferson/iptv-panel/main/docs/epgbrasil.m3u"
]


class M3UProcessor:
    def __init__(self):
        self.canais = []
        self.urls_vistas = set()

    def extrair_atributos(self, linha: str) -> dict:
        """Extrai atributos da linha EXTINF"""
        attrs = dict(regex_attr.findall(linha))
        return {
            "tvg_id": attrs.get("tvg-id", ""),
            "tvg_name": attrs.get("tvg-name", ""),
            "tvg_logo": attrs.get("tvg-logo", ""),
            "group": attrs.get("group-title", "OUTROS")
        }

    def extrair_nome(self, linha: str) -> str:
        """Extrai o nome do canal da linha EXTINF"""
        return linha.split(",")[-1].strip() if "," in linha else "Sem Nome"

    def limpar_texto(self, txt: str) -> str:
        return txt.strip() if txt else ""

    def processar_texto(self, conteudo: str) -> list:
        """Processa conteúdo M3U em texto e retorna lista de canais"""
        self.canais = []
        self.urls_vistas = set()
        dados_extinf = None

        for linha in conteudo.splitlines():
            linha = linha.strip()
            if not linha:
                continue

            if linha.startswith("#EXTINF"):
                attrs = self.extrair_atributos(linha)
                nome = self.extrair_nome(linha)
                dados_extinf = {
                    "nome": self.limpar_texto(nome) or "Sem Nome",
                    "tvg_id": self.limpar_texto(attrs["tvg_id"]),
                    "tvg_name": self.limpar_texto(attrs["tvg_name"]) or nome,
                    "tvg_logo": self.limpar_texto(attrs["tvg_logo"]),
                    "group": self.limpar_texto(attrs["group"]) or "OUTROS"
                }

            elif linha.startswith("http") or linha.startswith("rtmp") or linha.startswith("rtsp"):
                if linha not in self.urls_vistas:
                    self.urls_vistas.add(linha)
                    canal = dados_extinf.copy() if dados_extinf else {
                        "nome": "Sem Nome",
                        "tvg_id": "",
                        "tvg_name": "Sem Nome",
                        "tvg_logo": "",
                        "group": "OUTROS"
                    }
                    canal["url"] = linha
                    self.canais.append(canal)
                    dados_extinf = None

        return self.canais

    def processar_url(self, url: str, timeout: int = 30) -> list:
        """Baixa e processa uma playlist M3U a partir de uma URL"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; IPTVSystem/1.0)"
            }
            resp = requests.get(url, timeout=timeout, headers=headers)
            resp.raise_for_status()
            conteudo = resp.text
            return self.processar_texto(conteudo)
        except Exception as e:
            raise ValueError(f"Erro ao baixar playlist: {e}")

    def gerar_m3u(self, canais: list, nome_playlist: str = "IPTV System") -> str:
        """Gera conteúdo M3U a partir de lista de canais com header profissional"""
        epg_string = ",".join(EPG_URLS)
        linhas = [
            f'#EXTM3U url-tvg="{epg_string}"',
            f'#PLAYLISTV: '
            f'pltv-logo="https://cdn-icons-png.flaticon.com/256/25/25231.png" '
            f'pltv-name="{nome_playlist}" '
            f'pltv-description="Playlist IPTV Automática" '
            f'pltv-cover="https://images.icon-icons.com/2407/PNG/512/gitlab_icon_146171.png" '
            f'pltv-author="IPTV System" '
            f'pltv-site="https://github.com/josieljefferson/iptv-panel" '
            f'pltv-email="suporte@iptvsystem.com"',
            ""
        ]

        for c in canais:
            tvg_id = c.get("tvg_id", "").replace('"', "&quot;")
            tvg_name = (c.get("tvg_name", "") or c.get("nome", "")).replace('"', "&quot;")
            tvg_logo = c.get("tvg_logo", "").replace('"', "&quot;")
            group = c.get("group", "OUTROS").replace('"', "&quot;")
            nome = c.get("nome", "Sem Nome").replace('"', "&quot;")

            linhas.append(
                f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-name="{tvg_name}" '
                f'tvg-logo="{tvg_logo}" group-title="{group}",{nome}'
            )
            linhas.append(c.get("url", ""))
            linhas.append("")

        return "\n".join(linhas)

    def obter_grupos(self, canais: list) -> dict:
        """Retorna dicionário com grupos e contagem de canais"""
        grupos = {}
        for canal in canais:
            grupo = canal.get("group", "OUTROS")
            grupos[grupo] = grupos.get(grupo, 0) + 1
        return dict(sorted(grupos.items()))

    def obter_estatisticas(self, canais: list) -> dict:
        """Retorna estatísticas da playlist"""
        grupos = self.obter_grupos(canais)
        return {
            "total_canais": len(canais),
            "total_grupos": len(grupos),
            "grupos": grupos,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
