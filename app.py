from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///financas.db'
app.config['SECRET_KEY'] = 'chave_secreta_do_app'

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'index'

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    gastos = db.relationship('Gasto', backref='dono', lazy=True)
    economias = db.relationship('Economia', backref='dono', lazy=True)

class Gasto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(200), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Economia(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(200), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        usuario_recebido = request.form.get('usuario')
        senha_recebida = request.form.get('senha')

        senha_criptografada = generate_password_hash(senha_recebida)
        novo_usuario = User(username=usuario_recebido, password=senha_criptografada)

        db.session.add(novo_usuario)
        db.session.commit()

        return redirect(url_for('index'))

    return render_template('registro.html')

@app.route('/login', methods=['POST'])
def login():
    usuario_recebido = request.form.get('usuario')
    senha_recebida = request.form.get('senha')

    usuario_encontrado = User.query.filter_by(username=usuario_recebido).first()

    if usuario_encontrado and check_password_hash(usuario_encontrado.password, senha_recebida):
        login_user(usuario_encontrado)
        return redirect(url_for('dashboard'))
    else:
        flash("Usuário ou senha incorretos. Tente novamente.")
        return redirect(url_for('index'))

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    if request.method == 'POST':
        mensagem = request.form.get('mensagem')
        partes = mensagem.rsplit(' ', 1)
        
        if len(partes) == 2:
            descricao = partes[0]
            valor_texto = partes[1].replace(',', '.')
            try:
                valor_numero = float(valor_texto)
                novo_gasto = Gasto(descricao=descricao, valor=valor_numero, user_id=current_user.id)
                db.session.add(novo_gasto)
                db.session.commit()
            except ValueError:
                flash("Não entendi o valor. Use o formato: Descrição 15,50")
        else:
            flash("Formato inválido. Use espaço entre o nome e o valor. Ex: Lanche 15,50")
            
        return redirect(url_for('dashboard'))
        
    meus_gastos = Gasto.query.filter_by(user_id=current_user.id).all()
    total_gasto = sum(gasto.valor for gasto in meus_gastos)
    
    return render_template('dashboard.html', gastos=meus_gastos, total=total_gasto)

@app.route('/extrato')
@login_required
def extrato():
    meus_gastos = Gasto.query.filter_by(user_id=current_user.id).all()
    total_gasto = sum(gasto.valor for gasto in meus_gastos)
    
    return render_template('extrato.html', gastos=meus_gastos, total=total_gasto)

@app.route('/deletar_gasto/<int:id>', methods=['POST'])
@login_required
def deletar_gasto(id):
    gasto_para_apagar = Gasto.query.get(id)
    if gasto_para_apagar and gasto_para_apagar.user_id == current_user.id:
        db.session.delete(gasto_para_apagar)
        db.session.commit()
        flash("Gasto apagado com sucesso!")
    return redirect(url_for('extrato'))

@app.route('/economias', methods=['GET', 'POST'])
@login_required
def economias():
    if request.method == 'POST':
        mensagem = request.form.get('mensagem')
        partes = mensagem.rsplit(' ', 1)
        
        if len(partes) == 2:
            descricao = partes[0]
            valor_texto = partes[1].replace(',', '.')
            try:
                valor_numero = float(valor_texto)
                nova_economia = Economia(descricao=descricao, valor=valor_numero, user_id=current_user.id)
                db.session.add(nova_economia)
                db.session.commit()
            except ValueError:
                flash("Não entendi o valor. Use o formato: Descrição 15,50")
        else:
            flash("Formato inválido. Use espaço entre o nome e o valor. Ex: Poupança 100,00")
            
        return redirect(url_for('economias'))
        
    minhas_economias = Economia.query.filter_by(user_id=current_user.id).all()
    total_economias = sum(economia.valor for economia in minhas_economias)
    
    return render_template('economias.html', economias=minhas_economias, total_economias=total_economias)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)