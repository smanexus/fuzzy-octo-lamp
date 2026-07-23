# fuzzy-octo-lamp

## Fluxo de push (preferência do dono do repo)

Quando o usuário autorizar um push ("pode subir", "libera o push", etc.),
fazer o fluxo completo **por padrão**, sem precisar perguntar de novo:

1. Commit + push na branch de trabalho.
2. Abrir o Pull Request para a branch default (`main`).
3. Fazer o **merge** do PR.

Essa autorização é padrão para este repositório. Só pausar para confirmar se
houver algo destrutivo/incomum além do merge normal (ex.: force-push que
descarta histórico não mergeado, remoção de arquivos que o usuário não criou).
