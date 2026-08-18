# Treinamento Zabbix com IA  
## Módulo 1 - Arquitetura de Integração e Exportação de Dados

### 📌 Tópicos abordados
- Visão geral da API Zabbix  
- Métodos avançados: `history.get` e `trend.get`  
- Filtros e limites  
- Exportação em tempo real vs. em lote  
- Seleção de métricas relevantes  
- Feature Engineering  
- Uso de Dependent Items e Preprocessing  
- Estruturação de payload JSON  
- Script Python + Pandas  
- Webhook simulando envio de eventos  

---

## 🔧 Atividades práticas

### 1. Consulta de métricas específicas
Usar `history.get` para extrair dados de CPU de um host nos últimos 30 minutos.  
**Objetivo:** entender filtros de tempo e `itemid`.

---

### 2. Comparação de granularidade
Obter dados de memória RAM com `history.get` e `trend.get`, comparando granularidade e volume.  
**Objetivo:** perceber quando usar cada método.

---

### 3. Aplicação de filtros avançados
Configurar filtros para coletar apenas métricas acima de um threshold (ex.: CPU > 80%).  
**Objetivo:** aprender a limitar resultados e reduzir ruído.

---

### 4. Exportação em lote vs. tempo real
Criar dois scripts:  
1. Exportação em lote de 24h de métricas de rede.  
2. Exportação em tempo real (streaming) de eventos críticos.  
**Objetivo:** comparar performance e aplicabilidade.

---

### 5. Feature Engineering com Pandas
Usar dados obtidos via API para criar novas features, como média móvel de CPU ou taxa de crescimento de uso de disco.  
**Objetivo:** preparar dados para modelos de IA.

---

### 6. Uso de Dependent Items
Configurar item dependente que derive métricas de latência a partir de dados brutos de rede, aplicando preprocessing (regex ou cálculo matemático).  
**Objetivo:** reduzir carga no servidor e enriquecer dados.

---

### 7. Estruturação de payload JSON
Montar manualmente um payload JSON para `trend.get` com múltiplos filtros e validar a resposta.  
**Objetivo:** entender a estrutura e manipulação de parâmetros.

---

### 8. Webhook simulando envio de eventos
Criar um webhook que receba eventos de Zabbix e envie para um endpoint simulado (Flask ou FastAPI).  
**Objetivo:** treinar integração com sistemas externos.

---

## Execução pela CLI central

Na pasta `api_consulting`, instale as dependências e execute cada atividade pelo
mesmo comando principal. Se estiver na raiz do projeto, use o prefixo
`api_consulting/` no caminho do script:

```bash
python3 -m pip install -r requirements.txt
python3 pythonzbx.py <atividade> --integration
# ou, a partir da raiz do projeto:
python3 api_consulting/pythonzbx.py <atividade> --integration
```

O arquivo `.env` concentra `ZABBIX_URL`, `ZABBIX_HOST` e `ZABBIX_TOKEN`.
Use `.env.example` como referência e não versione credenciais.

Exemplos:

```bash
python3 pythonzbx.py 1 --integration --limit 100
python3 pythonzbx.py 3 --integration --threshold 80
python3 pythonzbx.py 7 --host-id 10001 --item-ids 20001 20002
python3 api_consulting/pythonzbx.py 8 --bind 0.0.0.0 --port 8080
```

As atividades 1 a 5 consultam a API real somente com `--integration`. As
atividades 6 e 7 podem ser executadas localmente para testar preprocessing e
payload. A atividade 8 inicia o endpoint HTTP em todas as interfaces e recebe
eventos JSON por `POST`, permitindo chamadas do Zabbix ou de outra máquina.

