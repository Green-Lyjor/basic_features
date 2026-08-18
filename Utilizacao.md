# Utilizacao da estrutura Zabbix

Este documento mostra como executar cada atividade pratica usando o comando
central `pythonzbx.py`.

## 1. Preparar o ambiente

Na raiz do projeto, ative o ambiente Python e entre na pasta da atividade:

```bash
cd "/Users/lyjorbarros/Documents/Cursos/Zabbix/Zabbix Ecossistemas e IA"
source agent_flows/.venv/bin/activate
cd api_consulting
```

O arquivo `.env` deve conter a configuracao do Zabbix:

```env
ZABBIX_URL=http://192.168.68.241/zabbix
ZABBIX_HOST=Zabbix server
ZABBIX_TOKEN=seu-token
```

O token deve permanecer somente no `.env`. Esse arquivo esta protegido pelo
`.gitignore` local.

Para instalar as dependencias em um ambiente novo:

```bash
python3 -m pip install -r requirements.txt
```

O comando principal sempre segue este formato:

```bash
python3 pythonzbx.py <atividade>
```

As atividades que consultam a API real precisam do argumento `--integration`.

## 2. Requisicoes diretas no Postman/cURL

As chamadas abaixo usam o mesmo endpoint JSON-RPC utilizado pelo script. No
Postman, cada bloco pode ser importado por **Import > Raw text** como cURL.

Defina as variaveis no terminal antes de executar os exemplos:

```bash
export ZABBIX_API="http://192.168.68.241/zabbix/api_jsonrpc.php"
export ZABBIX_TOKEN="seu-token"
export HOST_NAME="Linux"
```

No Postman, use uma variavel de ambiente chamada `zabbix_api` com o valor da
URL acima e outra chamada `zabbix_token` com o token. O header comum a todas as
chamadas JSON-RPC e:

```text
Content-Type: application/json-rpc
Authorization: Bearer {{zabbix_token}}
```

### 2.1 Descobrir o hostid

Antes das consultas, descubra o ID interno do host pelo nome. Este exemplo
retorna o host `Linux` ou qualquer nome colocado em `HOST_NAME`:

```bash
curl --request POST "$ZABBIX_API" \
  --header "Content-Type: application/json-rpc" \
  --header "Authorization: Bearer $ZABBIX_TOKEN" \
  --data @- <<EOF
{
  "jsonrpc": "2.0",
  "method": "host.get",
  "params": {
    "output": ["hostid", "host", "name"],
    "filter": {
      "host": ["$HOST_NAME"]
    }
  },
  "id": 1
}
EOF
```

Guarde o valor retornado em `hostid`. Para os exemplos seguintes:

```bash
export HOST_ID="10688"
```

O `hostid` pode ser diferente em outro ambiente.

### 2.2 Descobrir os itens de CPU

Esta chamada lista os itens de CPU do host. Ela corresponde à etapa de
descoberta da atividade 1:

```bash
curl --request POST "$ZABBIX_API" \
  --header "Content-Type: application/json-rpc" \
  --header "Authorization: Bearer $ZABBIX_TOKEN" \
  --data @- <<EOF
{
  "jsonrpc": "2.0",
  "method": "item.get",
  "params": {
    "output": ["itemid", "name", "key_", "value_type"],
    "hostids": ["$HOST_ID"]
  },
  "id": 2
}
EOF
```

Escolha o `itemid` do item desejado, por exemplo `42269`, e defina:

```bash
export CPU_ITEM_ID="42269"
export CPU_HISTORY_TYPE="0"
```

O `CPU_HISTORY_TYPE` vem do campo `value_type` retornado pelo `item.get`.

### 2.3 Atividade 1: history.get de CPU

Para buscar os ultimos 30 minutos, calcule os timestamps Unix e faça a
chamada. O exemplo abaixo usa macOS:

```bash
export TIME_TILL=$(date +%s)
export TIME_FROM=$((TIME_TILL - 30 * 60))

curl --request POST "$ZABBIX_API" \
  --header "Content-Type: application/json-rpc" \
  --header "Authorization: Bearer $ZABBIX_TOKEN" \
  --data @- <<EOF
{
  "jsonrpc": "2.0",
  "method": "history.get",
  "params": {
    "output": "extend",
    "itemids": ["$CPU_ITEM_ID"],
    "history": $CPU_HISTORY_TYPE,
    "time_from": $TIME_FROM,
    "time_till": $TIME_TILL,
    "sortfield": "clock",
    "sortorder": "ASC",
    "limit": 10
  },
  "id": 3
}
EOF
```

O campo `limit` nesta chamada limita o total de registros retornados pelo
Zabbix.

### 2.4 Atividade 2: history.get e trend.get de memoria

Descubra o item de memória com `item.get`, selecione o item de nome exato
`Memory utilization` e defina seus valores:

```bash
export MEMORY_ITEM_ID="51463"
export MEMORY_HISTORY_TYPE="0"
export TIME_TILL=$(date +%s)
export TIME_FROM=$((TIME_TILL - 60 * 60))
```

Consulta das amostras individuais com `history.get`:

```bash
curl --request POST "$ZABBIX_API" \
  --header "Content-Type: application/json-rpc" \
  --header "Authorization: Bearer $ZABBIX_TOKEN" \
  --data @- <<EOF
{
  "jsonrpc": "2.0",
  "method": "history.get",
  "params": {
    "output": "extend",
    "itemids": ["$MEMORY_ITEM_ID"],
    "history": $MEMORY_HISTORY_TYPE,
    "time_from": $TIME_FROM,
    "time_till": $TIME_TILL,
    "sortfield": "clock",
    "sortorder": "ASC",
    "limit": 100
  },
  "id": 4
}
EOF
```

Consulta agregada com `trend.get`:

```bash
curl --request POST "$ZABBIX_API" \
  --header "Content-Type: application/json-rpc" \
  --header "Authorization: Bearer $ZABBIX_TOKEN" \
  --data @- <<EOF
{
  "jsonrpc": "2.0",
  "method": "trend.get",
  "params": {
    "output": "extend",
    "itemids": ["$MEMORY_ITEM_ID"],
    "time_from": $TIME_FROM,
    "time_till": $TIME_TILL,
    "sortfield": "clock",
    "sortorder": "ASC",
    "limit": 100
  },
  "id": 5
}
EOF
```

### 2.5 Atividade 3: filtro de CPU acima de 80%

A API retorna as amostras; o filtro `value > 80` e aplicado pelo Python. Use
o mesmo cURL da atividade 1 e altere apenas o limite de dados, se necessario:

```bash
curl --request POST "$ZABBIX_API" \
  --header "Content-Type: application/json-rpc" \
  --header "Authorization: Bearer $ZABBIX_TOKEN" \
  --data @- <<EOF
{
  "jsonrpc": "2.0",
  "method": "history.get",
  "params": {
    "output": "extend",
    "itemids": ["$CPU_ITEM_ID"],
    "history": $CPU_HISTORY_TYPE,
    "time_from": $TIME_FROM,
    "time_till": $TIME_TILL,
    "sortfield": "clock",
    "sortorder": "ASC",
    "limit": 100
  },
  "id": 6
}
EOF
```

No Postman, use a aba **Tests** para filtrar a resposta:

```javascript
const result = pm.response.json().result;
const above80 = result.filter(row => Number(row.value) > 80);
console.log(above80);
```

### 2.6 Atividade 4: rede e eventos criticos

Depois de descobrir um item de rede via `item.get`, defina:

```bash
export NETWORK_ITEM_ID="itemid-da-rede"
export NETWORK_HISTORY_TYPE="3"
export TIME_TILL=$(date +%s)
export TIME_FROM=$((TIME_TILL - 24 * 60 * 60))
```

Exportacao das ultimas 24 horas:

```bash
curl --request POST "$ZABBIX_API" \
  --header "Content-Type: application/json-rpc" \
  --header "Authorization: Bearer $ZABBIX_TOKEN" \
  --data @- <<EOF
{
  "jsonrpc": "2.0",
  "method": "history.get",
  "params": {
    "output": "extend",
    "itemids": ["$NETWORK_ITEM_ID"],
    "history": $NETWORK_HISTORY_TYPE,
    "time_from": $TIME_FROM,
    "time_till": $TIME_TILL,
    "sortfield": "clock",
    "sortorder": "ASC",
    "limit": 100
  },
  "id": 7
}
EOF
```

Eventos recentes com severidade alta (4) ou desastre (5):

```bash
curl --request POST "$ZABBIX_API" \
  --header "Content-Type: application/json-rpc" \
  --header "Authorization: Bearer $ZABBIX_TOKEN" \
  --data @- <<EOF
{
  "jsonrpc": "2.0",
  "method": "problem.get",
  "params": {
    "output": "extend",
    "hostids": ["$HOST_ID"],
    "severities": [4, 5],
    "recent": true,
    "sortfield": ["eventid"],
    "sortorder": "DESC",
    "limit": 100
  },
  "id": 8
}
EOF
```

### 2.7 Atividade 5: dados para feature engineering

A coleta de CPU e a mesma da atividade 1. No Postman, envie novamente o
`history.get` e use este script na aba **Tests** para calcular a media movel
de cinco amostras:

```javascript
const rows = pm.response.json().result.map(row => ({
  clock: Number(row.clock),
  cpu: Number(row.value)
}));
const windowSize = 5;
const movingAverage = rows.map((row, index) => {
  const start = Math.max(0, index - windowSize + 1);
  const values = rows.slice(start, index + 1).map(item => item.cpu);
  return {...row, moving_average: values.reduce((sum, value) => sum + value, 0) / values.length};
});
console.log(movingAverage);
```

### 2.8 Atividade 6: preprocessing

Essa atividade nao faz requisicao ao Zabbix. Para testar somente a mesma
entrada pelo terminal:

```bash
python3 pythonzbx.py 6 --raw-latency "rtt=42.75ms"
```

O equivalente em JavaScript no Postman seria:

```javascript
const raw = "rtt=42.75ms";
const match = raw.match(/[-+]?\d+(?:\.\d+)?/);
pm.environment.set("latency_ms", Number(match[0]));
console.log(Number(match[0]));
```

### 2.9 Atividade 7: trend.get com multiplos filtros

Esta e a requisicao direta completa para a atividade 7:

```bash
curl --request POST "$ZABBIX_API" \
  --header "Content-Type: application/json-rpc" \
  --header "Authorization: Bearer $ZABBIX_TOKEN" \
  --data @- <<EOF
{
  "jsonrpc": "2.0",
  "method": "trend.get",
  "params": {
    "output": "extend",
    "hostids": ["$HOST_ID"],
    "itemids": ["$CPU_ITEM_ID", "$MEMORY_ITEM_ID"],
    "time_from": $TIME_FROM,
    "time_till": $TIME_TILL,
    "sortfield": "clock",
    "sortorder": "ASC",
    "limit": 100
  },
  "id": 9
}
EOF
```

### 2.10 Atividade 8: webhook local

A atividade 8 nao chama a API do Zabbix e nao precisa do token no `.env`.
Primeiro inicie o receptor e mantenha esse terminal aberto:

Se o terminal ja estiver dentro de `api_consulting`:

```bash
python3 pythonzbx.py 8 --bind 0.0.0.0 --port 8080
```

Se o terminal estiver na raiz do projeto `Zabbix Ecossistemas e IA`:

```bash
python3 api_consulting/pythonzbx.py 8 --bind 0.0.0.0 --port 8080
```

Outra alternativa e entrar na pasta antes de executar:

```bash
cd api_consulting
python3 pythonzbx.py 8 --bind 0.0.0.0 --port 8080
```

Execute esse comando em um terminal normal do macOS. O terminal automatizado
do VS Code pode bloquear a abertura de portas e produzir `PermissionError`,
mesmo quando o script esta correto.

O terminal deve mostrar `Webhook ouvindo em http://0.0.0.0:8080/`. Confirme que
existe um processo escutando:

```bash
lsof -nP -iTCP:8080 -sTCP:LISTEN
```

Depois envie o evento pelo Postman ou cURL para `127.0.0.1` se o teste for no
mesmo Mac:

```bash
curl --request POST "http://127.0.0.1:8080/" \
  --header "Content-Type: application/json" \
  --data '{
    "eventid": "demo-001",
    "host": "Linux",
    "severity": 4,
    "message": "CPU acima de 80%"
  }'
```

No Postman, use `POST http://127.0.0.1:8080/`, o header
`Content-Type: application/json` e o mesmo JSON no body **raw**.

Se o Zabbix estiver em outra maquina, descubra o IP do Mac na mesma rede:

```bash
ipconfig getifaddr en0
```

Use esse IP no teste e na configuracao do Zabbix, por exemplo
`http://192.168.68.50:8080/`. Nao use `192.168.68.241` a menos que o Python
tambem esteja executando nessa maquina. O processo Python precisa continuar
rodando; se ele for encerrado com `Ctrl+C`, a porta deixa de aceitar conexoes.

## 3. Atividade 1: metricas de CPU

Consulta os itens compatíveis com CPU que possuem dados nos ultimos 30 minutos
usando `history.get`:

```bash
python3 pythonzbx.py 1 --integration --host "Zabbix server"
```

Para limitar a quantidade de registros:

```bash
python3 pythonzbx.py 1 --integration --host "Zabbix server" --limit 100
```

O `--limit` e global para a atividade: com `--limit 1`, a resposta tera no
maximo um registro somando todos os itens de CPU encontrados. O tipo correto
de historico (`float`, `unsigned` etc.) e escolhido automaticamente a partir
do `value_type` de cada item no Zabbix.

Quando o host possui vários itens de CPU, somente os itens com dados são
retornados. Para consultar somente itens específicos, repita `--item-id`:

```bash
python3 pythonzbx.py 1 --integration \
  --host "Zabbix server" \
  --item-id 42256 \
  --item-id 42257
```

Saida esperada:

```json
{
  "activity": 1,
  "host": "Zabbix server",
  "items": [
    {
      "itemid": "42269",
      "name": "CPU utilization",
      "key_": "system.cpu.util"
    }
  ],
  "data": []
}
```

O campo `data` contem as amostras retornadas. Uma lista vazia significa que
nao houve amostras no periodo consultado.

## 4. Atividade 2: granularidade de memoria

Consulta memoria usando `history.get` e `trend.get`:

```bash
python3 pythonzbx.py 2 --integration --host "Linux"
```

Definindo um intervalo de 60 minutos:

```bash
python3 pythonzbx.py 2 --integration --host "Linux" --minutes 60 --limit 100
```

Para consultar 24 horas:

```bash
python3 pythonzbx.py 2 --integration --host "Linux" --minutes 1440 --limit 1000
```

A atividade prioriza o item com nome exato `Memory utilization`. No host
`Linux`, por exemplo, esse item e o `51463`; o item `Available memory in %`
nao e escolhido quando `Memory utilization` esta disponivel. A resposta possui
os campos `history` para amostras individuais e `trend` para dados agregados
pelo Zabbix.

## 5. Atividade 3: filtro por threshold

Busca CPU e mantem somente valores acima do limite definido:

```bash
python3 pythonzbx.py 3 --integration --threshold 80
```

Exemplo com limite de 90%:

```bash
python3 pythonzbx.py 3 --integration --threshold 90 --limit 500
```

O retorno inclui o threshold usado:

```json
{
  "activity": 3,
  "itemid": "42256",
  "data": [],
  "threshold": 80
}
```

O filtro e aplicado no Python depois da consulta a API.

## 6. Atividade 4: exportacao de rede e eventos criticos

Consulta dados de rede das ultimas 24 horas e problemas recentes com
severidade alta ou desastre:

```bash
python3 pythonzbx.py 4 --integration
```

Limitando os resultados:

```bash
python3 pythonzbx.py 4 --integration --limit 100
```

O resultado contem:

```json
{
  "activity": 4,
  "batch_network": [],
  "critical_events": []
}
```

`batch_network` representa a exportacao em lote e `critical_events` representa
os problemas recentes com severidade 4 ou 5.

Na implementacao atual, os eventos sao consultados uma vez. O modo streaming
continuo exigiria repetir a consulta em intervalos.

## 7. Atividade 5: feature engineering com Pandas

Consulta CPU e calcula uma media movel:

```bash
python3 pythonzbx.py 5 --integration
```

Usando uma janela de cinco amostras:

```bash
python3 pythonzbx.py 5 --integration --window 5 --limit 100
```

O retorno inclui `samples` e `cpu_moving_average`. O calculo principal utiliza
`pandas.Series.rolling()`.

## 8. Atividade 6: dependent item e preprocessing

Esta atividade simula o processamento de uma latencia recebida como texto.
Ela nao altera a configuracao do Zabbix.

Usando o valor padrao:

```bash
python3 pythonzbx.py 6
```

Informando outro valor:

```bash
python3 pythonzbx.py 6 --raw-latency "rtt=42.75ms"
```

Resultado esperado:

```json
{
  "activity": 6,
  "raw": "rtt=42.75ms",
  "latency_ms": 42.75,
  "preprocessing": "regex + conversao numerica"
}
```

O fluxo demonstrado e:

```text
valor bruto -> regex -> numero decimal -> latencia em milissegundos
```

## 9. Atividade 7: payload de trend.get

Monta e valida localmente um payload JSON para `trend.get`:

```bash
python3 pythonzbx.py 7 \
  --host-id 10001 \
  --item-ids 20001 20002 \
  --limit 100
```

Tambem e possivel definir o intervalo por timestamp Unix:

```bash
python3 pythonzbx.py 7 \
  --host-id 10001 \
  --item-ids 20001 20002 \
  --time-from 1787070000 \
  --time-till 1787077000
```

A resposta mostra o campo `payload` completo e `valid: true`. Essa atividade
valida a estrutura, mas nao executa a consulta na API.

## 10. Atividade 8: webhook acessivel externamente

Inicie o receptor HTTP local:

```bash
python3 pythonzbx.py 8
```

Por padrao, o servidor escuta em `0.0.0.0:8080`, aceitando conexoes de outras
maquinas. Se o script estiver na maquina `192.168.68.241`, o endereco para o
Zabbix sera:

```text
http://192.168.68.241:8080/
```

Para restringir o webhook a testes na propria maquina, use `127.0.0.1`.
Outra interface ou porta pode ser informada assim:

```bash
  python3 api_consulting/pythonzbx.py 8 --bind 0.0.0.0 --port 8080
```

Em outro terminal, envie um evento de teste:

```bash
curl -X POST http://127.0.0.1:8080/ \
  -H "Content-Type: application/json" \
  -d '{
    "eventid": "demo-001",
    "host": "Zabbix server",
    "severity": 4,
    "message": "CPU acima de 80%"
  }'
```

A resposta esperada possui `accepted: true` e repete o evento recebido.
Use `Ctrl+C` para encerrar o webhook.

### Configurar o Zabbix para enviar eventos

O exemplo abaixo considera que o Zabbix esta em `192.168.68.241` e que o
`pythonzbx.py` esta em outra maquina. Substitua `PYTHON_HOST` pelo IP da
maquina onde o processo Python esta executando:

```bash
export PYTHON_HOST="192.168.68.50"
```

1. Garanta que a porta TCP 8080 esteja liberada no sistema operacional e que o
  processo esteja em execucao:

    ```bash
    python3 pythonzbx.py 8 --bind 0.0.0.0 --port 8080
    ```

2. Teste a conectividade a partir do servidor Zabbix. Se o comando for
  executado no proprio servidor, use:

   ```bash
   curl --fail --request POST "http://$PYTHON_HOST:8080/" \
     --header "Content-Type: application/json" \
     --data '{"eventid":"manual-001","host":"Linux","severity":4,"message":"Teste do Zabbix"}'
   ```

  A resposta deve conter `"accepted": true`.

3. No frontend do Zabbix, abra **Alertas > Tipos de mídia** e crie um tipo de
  mídia chamado `Webhook Python`, com tipo **Webhook**.

4. Adicione estes parâmetros no tipo de mídia:

  ```text
  URL       = http://PYTHON_HOST:8080/
  event_id  = {EVENT.ID}
  host      = {HOST.NAME}
  severity  = {EVENT.SEVERITY}
  message   = {ALERT.MESSAGE}
  ```

5. No campo **Script** do tipo de mídia, cole o JavaScript abaixo. Ele monta
  o JSON e envia o evento ao endpoint Python:

  ```javascript
  var params = JSON.parse(value);
  var request = new HttpRequest();
  request.addHeader('Content-Type: application/json');

  var payload = {
     eventid: params.event_id,
     host: params.host,
     severity: params.severity,
     message: params.message
  };

  var response = request.post(params.URL, JSON.stringify(payload));
  var status = request.getStatus();

  if (status < 200 || status >= 300) {
     throw 'HTTP ' + status + ': ' + response;
  }

  return response;
  ```

6. Salve o tipo de mídia. Em **Usuários > seu usuário > Mídia**, adicione
  `Webhook Python`, informe qualquer destino exigido pela interface e deixe o
  período ativo. O URL real vem do parâmetro `URL` do tipo de mídia.

7. Abra **Alertas > Ações > Trigger actions** e crie ou edite uma ação de
  teste. Em **Condições**, escolha um host como `Linux` e, em **Operações**,
  adicione **Enviar mensagem** para o usuário que possui o tipo de mídia
  `Webhook Python`.

8. Provoque um evento de teste no host, por exemplo elevando temporariamente
  uma métrica monitorada, ou use **Monitoramento > Problemas** para confirmar
  que a ação foi disparada. Verifique o terminal do Python e o histórico em
  **Alertas > Log de ações**.

9. Para testar sem provocar um problema real, use primeiro o `curl` manual do
  passo 2. Depois use **Usuários > Mídia > Testar** no tipo de mídia, quando
  essa opção estiver disponível na versão do Zabbix instalada.

O binding `0.0.0.0` permite conexões de qualquer origem alcançável pela rede,
mas não substitui firewall ou autenticação. Para um ambiente fora do laboratório,
restrinja a porta ao IP do servidor Zabbix e adicione um segredo no payload ou
um proxy reverso com HTTPS.

## 11. Executar os testes

Para executar os testes unitarios:

```bash
python3 -m unittest -v test_pythonzbx.py
```

Para verificar a sintaxe:

```bash
python3 -m py_compile pythonzbx.py test_pythonzbx.py
```

O nome correto do comando e `pythonzbx.py`.