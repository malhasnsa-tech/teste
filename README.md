# Calculadora Online (com Login + Chave de Acesso)

App Flask com:
- Login por email/senha
- Cadastro protegido por **chave de acesso** (convite)
- Página da **calculadora** protegida (somente logado)
- Banco SQLite

## Como rodar localmente
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edite o SECRET_KEY e ADMIN_INVITE_KEY se quiser
python app.py
# Acesse http://localhost:8000
```

## Criar chaves de acesso
A aplicação cria automaticamente uma chave master a partir da variável de ambiente `ADMIN_INVITE_KEY` (padrão do .env.example).  
Você também pode criar chaves manualmente via rota `POST /admin/keys/create` (precisa estar logado como admin; para tornar alguém admin, atualize no SQLite).

## Deploy rápido (Render.com)
1. Crie um novo Web Service apontando para este repositório/ZIP
2. Build: `pip install -r requirements.txt`
3. Start: `gunicorn app:app -b 0.0.0.0:$PORT`
4. Defina envs: `SECRET_KEY`, `ADMIN_INVITE_KEY`
5. Acesse a URL gerada

## Deploy com Docker
```Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PORT=8000
CMD ["gunicorn", "app:app", "-b", "0.0.0.0:8000"]
```
```bash
docker build -t calc-online .
docker run -p 8000:8000 --env SECRET_KEY=seu_segredo --env ADMIN_INVITE_KEY=SUA-CHAVE calc-online
```

## Login de teste
1. Cadastre-se usando a chave do `.env.example`: `MASTER-KEY-EXEMPLO-1234`
2. Faça login e acesse a calculadora
