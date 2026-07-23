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

O `Procfile` já sobe com gunicorn (`web: gunicorn app:app`). No Railway basta
apontar para o repositório; a porta vem da variável de ambiente `PORT`.

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

- Notificações no celular via Web Push (PWA + Service Worker)
- Login por pessoa
