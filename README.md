# Escala de Louvor

Webapp em Flask para consultar a escala do grupo de louvor. Você busca pelo seu
nome e vê suas próximas escalas, sua função em cada dia e, ao abrir um dia,
quem mais está escalado com você.

Duas escalas convivem no mesmo app:

- **Ichthus** — cultos de **Sábado** (`data/ichthus.csv`)
- **Doulos** — cultos de **Domingo** (`data/doulos.csv`)

## Como funciona

Os dois CSVs são a fonte de dados (sem banco por enquanto — é só leitura). Cada
linha é uma função, cada coluna é uma data, e a célula diz quem serve. Uma mesma
pessoa pode aparecer em mais de uma função no mesmo dia — isso é tratado como um
único dia com várias funções.

Páginas:

- `/` — busca por nome
- `/pessoa/<slug>` — próximas escalas da pessoa (e um histórico recolhível)
- `/escala/<escala>/<data>` — time completo daquele dia

## Rodar localmente

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py
# abre em http://localhost:5000
```

## Deploy no Railway

O `Procfile` já sobe com gunicorn (`web: gunicorn app:app --bind 0.0.0.0:$PORT`).
No Railway basta apontar para o repositório; a porta vem da variável `PORT`.

### Variáveis de ambiente

| Variável | Para quê | Obrigatória |
|---|---|---|
| `VAPID_PRIVATE_KEY` | Chave privada do Web Push. Gere com `python gen_vapid.py`. | Sim (para push) |
| `VAPID_CLAIM_EMAIL` | E-mail de contato do remetente, ex.: `mailto:voce@igreja.com`. | Recomendada |
| `REMINDER_TOKEN` | Senha que protege o endpoint `/tasks/send-reminders`. | Sim (para lembretes) |
| `DB_PATH` | Caminho do SQLite das inscrições. Aponte para um volume persistente. | Recomendada |
| `REMINDER_DAYS` | Reservado para ajustes futuros. Padrão `1`. | Não |

> **Persistência no Railway:** o disco padrão é efêmero (some a cada deploy).
> Crie um **Volume** (ex.: montado em `/data`) e defina `DB_PATH=/data/push.db`
> para não perder as inscrições de notificação a cada atualização.

## Notificações (Web Push / PWA)

O app é um PWA instalável ("adicionar à tela de início"). Cada pessoa abre a
própria página e toca em **Ativar** para receber notificações naquele aparelho.

- No **Android** funciona direto no Chrome.
- No **iPhone** só funciona depois de **adicionar à tela de início** (exigência
  da Apple); então abrir pelo ícone e ativar.

### Lembrete do fim de semana

`send_reminders.py` / o endpoint `/tasks/send-reminders` avisam **quem está na
escala do próximo fim de semana**, dizendo o ministério (Ichthus no sábado,
Doulos no domingo, ou ambos) e a(s) função(ões). A ideia é rodar **segunda de
manhã**.

Formas de acionar (escolha uma):

```bash
# 1) Railway Cron Service apontando para:
python send_reminders.py

# 2) Cron externo (ex.: cron-job.org) fazendo GET em:
#    https://SEU-APP/tasks/send-reminders?token=SEU_REMINDER_TOKEN
```

Para testar com uma data específica (finge que "hoje" é essa segunda):

```bash
python send_reminders.py 2026-08-03
```

## Logos

Coloque as imagens em `static/`:

- `static/img/alvorada.png` — logo da igreja (aparece na home e vira o ícone do PWA).
- (opcional) logos de Ichthus e Doulos para os cards.

Os ícones do PWA ficam em `static/icons/` (atualmente placeholders marrom;
substitua por versões geradas a partir da logo da Alvorada nos tamanhos
192, 512 e maskable-512).

## Atualizar a escala

Substitua os arquivos em `data/` (mantendo o formato: separador `;`, primeira
coluna com o nome da função, primeira linha com as datas em `dd/mm/aa`). Se
exportar de uma planilha em Latin-1/ISO-8859-1, converta para UTF-8 antes:

```bash
iconv -f ISO-8859-1 -t UTF-8 origem.csv > data/ichthus.csv
```

Nomes escritos de formas diferentes que são a mesma pessoa podem ser unificados
no mapa `NAME_ALIASES` em `data_loader.py`.

## Próximos passos

- Trocar os placeholders pelas logos reais (Alvorada, Ichthus, Doulos)
- Definir e agendar o gatilho do lembrete (segunda de manhã)
- Login por pessoa
