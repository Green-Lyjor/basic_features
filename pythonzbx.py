#!/usr/bin/env python3
"""CLI central para as atividades práticas de integração com a API do Zabbix."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent


def load_env(path: Path = ROOT / ".env") -> None:
    """Carrega um .env pequeno sem sobrescrever variáveis já exportadas."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


class ZabbixAPIError(RuntimeError):
    """Representa erros de transporte ou erros retornados pela API do Zabbix."""

    pass


class ZabbixClient:
    """Cliente mínimo para executar chamadas JSON-RPC autenticadas no Zabbix."""

    def __init__(self, url: str, token: str, timeout: int = 30) -> None:
        """Prepara o endpoint da API, o token Bearer e o timeout das requisições."""
        self.url = url.rstrip("/") + "/api_jsonrpc.php"
        self.token = token
        self.timeout = timeout
        self._request_id = 0

    def call(self, method: str, params: dict[str, Any]) -> Any:
        """Envia um método JSON-RPC e retorna seu resultado ou lança erro detalhado."""
        self._request_id += 1
        payload = {"jsonrpc": "2.0", "method": method, "params": params, "id": self._request_id}
        request = Request(
            self.url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json-rpc", "Authorization": f"Bearer {self.token}"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError) as exc:
            raise ZabbixAPIError(f"Falha ao acessar {self.url}: {exc}") from exc
        if "error" in result:
            error = result["error"]
            raise ZabbixAPIError(f"{error.get('data', error.get('message', 'erro desconhecido'))}")
        return result.get("result")


def epoch_minutes(minutes: int) -> tuple[int, int]:
    """Converte uma janela em minutos no par de timestamps inicial e final."""
    end = int(time.time())
    return end - minutes * 60, end


def host_id(client: ZabbixClient, host: str) -> str:
    """Localiza o identificador interno de um host pelo nome configurado no Zabbix."""
    hosts = client.call("host.get", {"output": ["hostid", "host"], "filter": {"host": [host]}})
    if not hosts:
        raise ZabbixAPIError(f"Host não encontrado: {host}")
    return hosts[0]["hostid"]


def matching_items(client: ZabbixClient, host: str, patterns: Iterable[str]) -> list[dict[str, Any]]:
    """Retorna todos os itens do host cujo nome ou chave contenha um padrão."""
    hid = host_id(client, host)
    items = client.call("item.get", {"output": ["itemid", "name", "key_", "value_type"], "hostids": [hid]})
    lowered = tuple(pattern.lower() for pattern in patterns)
    matches = []
    for item in items:
        text = f"{item.get('name', '')} {item.get('key_', '')}".lower()
        if any(pattern in text for pattern in lowered):
            matches.append(item)
    if not matches:
        raise ZabbixAPIError(f"Item não encontrado no host {host}: {', '.join(lowered)}")
    return sorted(matches, key=lambda item: (item.get("name", "").lower() != "cpu utilization", item.get("name", "").lower()))


def item_id(client: ZabbixClient, host: str, patterns: Iterable[str]) -> str:
    """Retorna o primeiro item compatível para atividades que usam uma métrica única."""
    return matching_items(client, host, patterns)[0]["itemid"]


def history(client: ZabbixClient, itemid: str, minutes: int, limit: int = 1000, history_type: str | None = None) -> list[dict[str, Any]]:
    """Busca amostras históricas de um item no intervalo e limite informados."""
    return history_items(client, [itemid], minutes, limit, history_type)


def history_items(client: ZabbixClient, itemids: list[str], minutes: int, limit: int = 1000, history_type: str | None = None) -> list[dict[str, Any]]:
    """Busca amostras de vários itens com um limite total para a resposta."""
    time_from, time_till = epoch_minutes(minutes)
    params = {"output": "extend", "itemids": itemids, "time_from": time_from, "time_till": time_till, "sortfield": "clock", "sortorder": "ASC", "limit": limit}
    if history_type is not None:
        params["history"] = int(history_type)
    return client.call("history.get", params)


def activity_1(client: ZabbixClient, args: argparse.Namespace) -> dict[str, Any]:
    """Executa a atividade 1 para todos os itens de CPU selecionados do host."""
    patterns = ("cpu utilization", "system.cpu.util", "cpu")
    items = matching_items(client, args.host, patterns)
    selected = set(getattr(args, "item_id", []))
    if selected:
        items = [item for item in items if item["itemid"] in selected]
        if not items:
            raise ZabbixAPIError(f"Nenhum --item-id pertence aos itens de CPU do host {args.host}")
    item_data = []
    data = []
    remaining = args.limit
    for item in items:
        if remaining <= 0:
            rows = []
        else:
            rows = history(client, item["itemid"], 30, remaining, item.get("value_type"))
            remaining -= len(rows)
        if rows:
            item_data.append({"itemid": item["itemid"], "name": item["name"], "key_": item["key_"]})
            data.extend([{**row, "itemid": item["itemid"], "item_name": item["name"], "item_key": item["key_"]} for row in rows])
    return {"activity": 1, "host": args.host, "items": item_data, "data": data}


def activity_2(client: ZabbixClient, args: argparse.Namespace) -> dict[str, Any]:
    """Compara amostras de memória de history.get com agregações de trend.get."""
    items = matching_items(client, args.host, ("memory utilization", "vm.memory.util", "memory"))
    selected = next((item for item in items if item.get("name", "").lower() == "memory utilization"), items[0])
    iid = selected["itemid"]
    start, end = epoch_minutes(args.minutes)
    return {"activity": 2, "itemid": iid, "item_name": selected["name"], "item_key": selected["key_"], "history": history(client, iid, args.minutes, args.limit, selected.get("value_type")), "trend": client.call("trend.get", {"output": "extend", "itemids": [iid], "time_from": start, "time_till": end, "sortfield": "clock", "sortorder": "ASC"})}


def activity_3(client: ZabbixClient, args: argparse.Namespace) -> dict[str, Any]:
    """Filtra os dados de CPU da atividade 1 mantendo valores acima do threshold."""
    result = activity_1(client, args)
    result["activity"] = 3
    result["data"] = [row for row in result["data"] if float(row.get("value", 0)) > args.threshold]
    result["threshold"] = args.threshold
    return result


def activity_4(client: ZabbixClient, args: argparse.Namespace) -> dict[str, Any]:
    """Exporta rede das últimas 24 horas e lista problemas recentes críticos."""
    iid = item_id(client, args.host, ("network", "net.if"))
    start, end = epoch_minutes(24 * 60)
    batch = client.call("history.get", {"output": "extend", "itemids": [iid], "time_from": start, "time_till": end, "sortfield": "clock", "sortorder": "ASC", "limit": args.limit})
    events = client.call("problem.get", {"output": "extend", "hostids": [host_id(client, args.host)], "severities": [4, 5], "recent": True, "sortfield": ["eventid"], "sortorder": "DESC", "limit": args.limit})
    return {"activity": 4, "batch_network": batch, "critical_events": events}


def activity_5(client: ZabbixClient, args: argparse.Namespace) -> dict[str, Any]:
    """Calcula uma média móvel de CPU usando Pandas quando disponível."""
    rows = activity_1(client, args)["data"]
    values = [float(row["value"]) for row in rows]
    try:
        import pandas as pd
    except ModuleNotFoundError:
        window = max(1, args.window)
        moving = [sum(values[max(0, index - window + 1): index + 1]) / min(window, index + 1) for index in range(len(values))]
    else:
        series = pd.Series(values, dtype="float64")
        moving = series.rolling(window=max(1, args.window), min_periods=1).mean().tolist()
    return {"activity": 5, "samples": len(values), "cpu_moving_average": moving}


def activity_6(client: ZabbixClient, args: argparse.Namespace) -> dict[str, Any]:
    """Simula preprocessing de dependent item extraindo latência numérica via regex."""
    raw = args.raw_latency
    match = re.search(r"[-+]?\d+(?:\.\d+)?", raw)
    if not match:
        raise ValueError("--raw-latency precisa conter um número")
    milliseconds = float(match.group())
    return {"activity": 6, "raw": raw, "latency_ms": milliseconds, "preprocessing": "regex + conversão numérica"}


def activity_7(client: ZabbixClient, args: argparse.Namespace) -> dict[str, Any]:
    """Monta e valida localmente o payload JSON-RPC para uma consulta trend.get."""
    payload = {"jsonrpc": "2.0", "method": "trend.get", "params": {"output": "extend", "hostids": [args.host_id], "itemids": args.item_ids, "time_from": args.time_from, "time_till": args.time_till, "limit": args.limit}, "id": 1}
    json.dumps(payload)
    return {"activity": 7, "payload": payload, "valid": True}


class WebhookHandler(BaseHTTPRequestHandler):
    """Recebe eventos JSON e devolve uma confirmação HTTP para testes locais."""

    received: list[dict[str, Any]] = []

    def do_POST(self) -> None:  # noqa: N802
        """Lê o corpo JSON do POST, armazena o evento e responde com status 200."""
        length = int(self.headers.get("Content-Length", "0"))
        data = json.loads(self.rfile.read(length) or b"{}")
        self.received.append(data)
        body = json.dumps({"accepted": True, "event": data}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args: Any) -> None:
        """Silencia o log padrão do servidor para manter a saída da CLI limpa."""
        return


def activity_8(_client: ZabbixClient, args: argparse.Namespace) -> dict[str, Any]:
    """Inicia o webhook local e mantém o servidor ativo até receber interrupção."""
    try:
        server = HTTPServer((args.bind, args.port), WebhookHandler)
    except PermissionError as exc:
        raise RuntimeError(
            f"Sem permissão para abrir {args.bind}:{args.port}. "
            "Execute no terminal real do macOS, autorize o firewall se solicitado "
            "e confirme que a porta não está bloqueada pelo ambiente do VS Code."
        ) from exc
    except OSError as exc:
        raise RuntimeError(f"Não foi possível abrir {args.bind}:{args.port}: {exc}") from exc
    print(f"Webhook ouvindo em http://{args.bind}:{args.port}/", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
    return {"activity": 8, "received": len(WebhookHandler.received)}


ACTIVITIES = {1: activity_1, 2: activity_2, 3: activity_3, 4: activity_4, 5: activity_5, 6: activity_6, 7: activity_7, 8: activity_8}


def build_parser() -> argparse.ArgumentParser:
    """Cria o parser da CLI com opções comuns a todas as atividades."""
    parser = argparse.ArgumentParser(description="Atividades práticas Zabbix via uma CLI central")
    parser.add_argument("activity", type=int, choices=range(1, 9), help="atividade do README (1 a 8)")
    parser.add_argument("--host", default=os.getenv("ZABBIX_HOST", "192.168.68.241"))
    parser.add_argument("--url", default=os.getenv("ZABBIX_URL", "http://192.168.68.241/zabbix"))
    parser.add_argument("--token", default=os.getenv("ZABBIX_TOKEN"))
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--minutes", type=int, default=60)
    parser.add_argument("--threshold", type=float, default=80)
    parser.add_argument("--window", type=int, default=5)
    parser.add_argument("--raw-latency", default="latency=42.5ms")
    parser.add_argument("--host-id", default="")
    parser.add_argument("--item-id", action="append", default=[], help="filtra um item específico; pode ser repetido")
    parser.add_argument("--item-ids", nargs="*", default=[], help="itemids usados apenas no payload da atividade 7")
    parser.add_argument("--time-from", type=int, default=int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp()))
    parser.add_argument("--time-till", type=int, default=int(datetime.now(timezone.utc).timestamp()))
    parser.add_argument("--bind", default="0.0.0.0", help="interface de escuta do webhook; 0.0.0.0 aceita conexões externas")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--integration", action="store_true", help="executa contra a API real; sem isso as atividades 1-5 exigem cliente de teste")
    return parser


def main(argv: list[str] | None = None, client: ZabbixClient | None = None) -> int:
    """Carrega configuração, seleciona a atividade e imprime seu resultado JSON."""
    load_env()
    args = build_parser().parse_args(argv)
    if args.activity == 7 and not args.host_id:
        args.host_id = host_id(client, args.host) if client else ""
    if client is None:
        if args.activity == 8:
            result = ACTIVITIES[args.activity](None, args)
            if result is not None:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if not args.token:
            raise SystemExit("ZABBIX_TOKEN não configurado; use .env ou --token")
        client = ZabbixClient(args.url, args.token)
    if not args.integration and args.activity in range(1, 6):
        raise SystemExit("As atividades 1-5 precisam de --integration quando executadas fora dos testes")
    result = ACTIVITIES[args.activity](client, args)
    if result is not None:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ZabbixAPIError, RuntimeError, ValueError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        raise SystemExit(1)