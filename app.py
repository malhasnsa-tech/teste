import os, sqlite3, hashlib, secrets
from flask import Flask, render_template, request, redirect, url_for, session, abort, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY','dev-secret')
DB_PATH = os.path.join(os.path.dirname(__file__), 'app.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with app.app_context():
        conn = get_db()
        with open(os.path.join(os.path.dirname(__file__), 'schema.sql'), 'r', encoding='utf-8') as f:
            conn.executescript(f.read())
        conn.commit()

def ensure_admin_key():
    # Garantir que exista uma chave master configurada em variável de ambiente
    admin_key = os.environ.get('ADMIN_INVITE_KEY')
    if not admin_key:
        return
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT id FROM access_keys WHERE key=?', (admin_key,))
    if not cur.fetchone():
        cur.execute('INSERT INTO access_keys(key,label,max_uses,used_count,active) VALUES (?,?,?,?,?)',
                    (admin_key, 'MASTER (ENV)', 10_000, 0, 1))
        conn.commit()

@app.before_first_request
def startup():
    if not os.path.exists(DB_PATH):
        init_db()
    ensure_admin_key()

def current_user():
    return session.get('user')

def login_required(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user():
            return redirect(url_for('login', next=request.path))
        return fn(*args, **kwargs)
    return wrapper

@app.get('/')
def index():
    if current_user():
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email','').strip().lower()
        password = request.form.get('password','')
        conn = get_db(); cur = conn.cursor()
        cur.execute('SELECT id,name,email,password_hash,is_admin FROM users WHERE email=?', (email,))
        row = cur.fetchone()
        if row and check_password_hash(row['password_hash'], password):
            session['user'] = dict(id=row['id'], name=row['name'], email=row['email'], is_admin=bool(row['is_admin']))
            next_url = request.args.get('next') or url_for('dashboard')
            return redirect(next_url)
        return render_template('login.html', error='Credenciais inválidas.')
    return render_template('login.html', error=None)

@app.route('/logout')
def logout():
    session.clear()
    flash('Você saiu com sucesso.')
    return redirect(url_for('login'))

def validate_and_consume_key(key, conn):
    cur = conn.cursor()
    cur.execute('SELECT id,key,label,max_uses,used_count,active,expires_at FROM access_keys WHERE key=?', (key,))
    k = cur.fetchone()
    if not k or k['active'] == 0:
        return False, 'Chave inválida ou inativa.'
    # expiração
    if k['expires_at']:
        import datetime
        try:
            if datetime.datetime.fromisoformat(k['expires_at']) < datetime.datetime.utcnow():
                return False, 'Chave expirada.'
        except Exception:
            pass
    if k['used_count'] >= k['max_uses']:
        return False, 'Chave esgotada.'
    # consumir
    cur.execute('UPDATE access_keys SET used_count = used_count + 1 WHERE id=?', (k['id'],))
    conn.commit()
    return True, None

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name','').strip()
        email = request.form.get('email','').strip().lower()
        password = request.form.get('password','')
        invite_key = request.form.get('invite_key','').strip()
        if not all([name,email,password,invite_key]):
            return render_template('register.html', error='Preencha todos os campos.')
        conn = get_db(); cur = conn.cursor()
        ok, err = validate_and_consume_key(invite_key, conn)
        if not ok:
            return render_template('register.html', error=err)
        try:
            cur.execute('INSERT INTO users(name,email,password_hash,is_admin) VALUES (?,?,?,?)',
                        (name,email,generate_password_hash(password),0))
            conn.commit()
        except sqlite3.IntegrityError:
            return render_template('register.html', error='Email já cadastrado.')
        flash('Conta criada com sucesso. Faça login.')
        return redirect(url_for('login'))
    return render_template('register.html', error=None)

@app.get('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

# Rotas administrativas simples para gerar chaves (só admin logado)
@app.post('/admin/keys/create')
@login_required
def create_key():
    if not current_user().get('is_admin'):
        abort(403)
    import datetime
    key = request.form.get('key') or secrets.token_urlsafe(10).upper()
    label = request.form.get('label') or 'Key gerada'
    max_uses = int(request.form.get('max_uses') or 1)
    expires_at = request.form.get('expires_at') or None
    conn = get_db(); cur = conn.cursor()
    cur.execute('INSERT INTO access_keys(key,label,max_uses,used_count,active,expires_at) VALUES (?,?,?,?,?,?)',
                (key,label,max_uses,0,1,expires_at))
    conn.commit()
    flash(f'Chave criada: {key} (usos: {max_uses})')
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    init_db(); ensure_admin_key()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8000)), debug=True)
