import os
from datetime import datetime, date
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from sqlalchemy import func, extract
from dateutil.relativedelta import relativedelta 

app = Flask(__name__)
app.config['SECRET_KEY'] = 'uma-chave-muito-segura'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///financas.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    meta_mensal = db.Column(db.Float, default=1000.0) 

class Gasto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(200), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    categoria = db.Column(db.String(50), default="Outros")
    data = db.Column(db.DateTime, default=datetime.utcnow) 
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Economia(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(200), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    valor_meta = db.Column(db.Float, default=0.0) 
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def identificar_categoria(texto):
    texto = texto.lower()
    categorias = {
        "Alimentação": ["99 food", "99food", "ifood", "lanche", "comida", "almoço", "jantar", "mercado", "pizza", "café", "alimentação"],
        "Transporte": ["99", "uber", "ônibus", "onibus", "gasolina", "combustivel", "metrô", "metro", "oficina"],
        "Lazer": ["cinema", "festa", "viagem", "show", "jogo", "praia", "role"],
        "Assinaturas": ["netflix", "spotify", "prime", "internet", "assinatura"],
        "Casa": ["aluguel", "luz", "água", "energia", "limpeza", "casa", "condominio"]
    }
    for categoria, palavras in categorias.items():
        for palavra in palavras:
            if palavra in texto: return categoria
    return "Outros"

MESES_NOME = {
    1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
    5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
    9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
}

def obter_mes_ano_selecionado():
    mes = request.args.get('mes')
    ano = request.args.get('ano')
    
    if not mes or not mes.isdigit() or not (1 <= int(mes) <= 12):
        mes = datetime.now().month
    else:
        mes = int(mes)
        
    if not ano or not ano.isdigit():
        ano = datetime.now().year
    else:
        ano = int(ano)
        
    return mes, ano

def obter_anos_disponiveis():
    ano_atual = datetime.now().year
    return [ano_atual - 1, ano_atual, ano_atual + 1, ano_atual + 2]

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('usuario')
        password = request.form.get('senha')
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Usuário ou senha incorretos.')
    return render_template('login.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        username = request.form.get('usuario')
        password = request.form.get('senha')
        if User.query.filter_by(username=username).first():
            flash('Este usuário já existe.')
        else:
            novo_usuario = User(username=username, password=password)
            db.session.add(novo_usuario)
            db.session.commit()
            return redirect(url_for('login'))
    return render_template('registro.html')

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    mes_selecionado, ano_selecionado = obter_mes_ano_selecionado()
    
    if request.method == 'POST':
        mensagem = request.form.get('mensagem')
        mes_tela = int(request.form.get('mes_tela', datetime.now().month))
        ano_tela = int(request.form.get('ano_tela', datetime.now().year))
        
        try:
            partes = mensagem.rsplit(' ', 1)
            desc = partes[0]
            valor = float(partes[1].replace(',', '.'))
            
            hoje = datetime.now()
            try:
                data_ajustada = hoje.replace(year=ano_tela, month=mes_tela)
            except ValueError:
                data_ajustada = hoje.replace(year=ano_tela, month=mes_tela, day=28)
            
            db.session.add(Gasto(descricao=desc, valor=valor, categoria=identificar_categoria(desc), user_id=current_user.id, data=data_ajustada))
            db.session.commit()
            
            return redirect(url_for('dashboard', mes=mes_tela, ano=ano_tela))
        except:
            flash('Erro! Digite: Descrição Valor (Ex: Pizza 50)')
            
    gastos = Gasto.query.filter_by(user_id=current_user.id)\
        .filter(extract('month', Gasto.data) == mes_selecionado)\
        .filter(extract('year', Gasto.data) == ano_selecionado)\
        .order_by(Gasto.data.desc()).all()
        
    total = sum(g.valor for g in gastos)
    anos = obter_anos_disponiveis()
    
    return render_template('dashboard.html', gastos=gastos, total=total, mes_atual=mes_selecionado, ano_atual=ano_selecionado, meses=MESES_NOME, anos=anos)


@app.route('/lancamento_detalhado', methods=['POST'])
@login_required
def lancamento_detalhado():
    descricao = request.form.get('descricao')
    valor_total = float(request.form.get('valor').replace(',', '.'))
    categoria = request.form.get('categoria')
    data_texto = request.form.get('data_compra')
    parcelas = int(request.form.get('parcelas'))

    data_inicial = datetime.strptime(data_texto, '%Y-%m-%d')
    valor_parcela = valor_total / parcelas

    for i in range(parcelas):
        desc_final = descricao if parcelas == 1 else f"{descricao} ({i+1}/{parcelas})"
        
        data_parcela = data_inicial + relativedelta(months=i)

        novo_gasto = Gasto(
            descricao=desc_final,
            valor=valor_parcela,
            categoria=categoria,
            data=data_parcela,
            user_id=current_user.id
        )
        db.session.add(novo_gasto)

    db.session.commit()
    
    return redirect(url_for('dashboard', mes=data_inicial.month, ano=data_inicial.year))


@app.route('/extrato', methods=['GET', 'POST'])
@login_required
def extrato():
    mes_selecionado, ano_selecionado = obter_mes_ano_selecionado()
    
    if request.method == 'POST' and 'nova_meta' in request.form:
        current_user.meta_mensal = float(request.form.get('nova_meta'))
        db.session.commit()
        
    gastos = Gasto.query.filter_by(user_id=current_user.id)\
        .filter(extract('month', Gasto.data) == mes_selecionado)\
        .filter(extract('year', Gasto.data) == ano_selecionado)\
        .order_by(Gasto.data.desc()).all()
        
    total = sum(g.valor for g in gastos)
    porcentagem = (total / current_user.meta_mensal * 100) if current_user.meta_mensal > 0 else 0
    anos = obter_anos_disponiveis()
    
    return render_template('extrato.html', gastos=gastos, total=total, porcentagem=min(porcentagem, 100), meta=current_user.meta_mensal, mes_atual=mes_selecionado, ano_atual=ano_selecionado, meses=MESES_NOME, anos=anos)

@app.route('/tabelas')
@login_required
def tabelas():
    mes_selecionado, ano_selecionado = obter_mes_ano_selecionado()
    
    resumo = db.session.query(Gasto.categoria, func.sum(Gasto.valor))\
        .filter_by(user_id=current_user.id)\
        .filter(extract('month', Gasto.data) == mes_selecionado)\
        .filter(extract('year', Gasto.data) == ano_selecionado)\
        .group_by(Gasto.categoria).all()
        
    labels = [r[0] for r in resumo]
    valores = [float(r[1]) for r in resumo]
    anos = obter_anos_disponiveis()
    
    return render_template('tabelas.html', resumo=resumo, labels=labels, valores=valores, mes_atual=mes_selecionado, ano_atual=ano_selecionado, meses=MESES_NOME, anos=anos)

@app.route('/economias', methods=['GET', 'POST'])
@login_required
def economias():
    if request.method == 'POST':
        if 'btn_criar' in request.form:
            nome = request.form.get('nome_meta')
            v_meta = float(request.form.get('valor_meta').replace(',', '.'))
            db.session.add(Economia(descricao=nome, valor=0, valor_meta=v_meta, user_id=current_user.id))
        elif 'btn_adicionar' in request.form:
            m_id = request.form.get('meta_id')
            v_add = float(request.form.get('valor_add').replace(',', '.'))
            meta = Economia.query.get(m_id)
            if meta and meta.user_id == current_user.id:
                meta.valor += v_add
        db.session.commit()
        return redirect(url_for('economias'))
    economias = Economia.query.filter_by(user_id=current_user.id).all()
    total_economias = sum(e.valor for e in economias) 
    return render_template('economias.html', economias=economias, total_economias=total_economias)

@app.route('/deletar_gasto/<int:id>', methods=['POST'])
@login_required
def deletar_gasto(id):
    gasto = Gasto.query.get(id)
    if gasto and gasto.user_id == current_user.id:
        db.session.delete(gasto); db.session.commit()
    return redirect(request.referrer or url_for('extrato'))

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/deletar_economia/<int:id>', methods=['POST'])
@login_required
def deletar_economia(id):
    eco = Economia.query.get(id)
    if eco and eco.user_id == current_user.id:
        db.session.delete(eco); db.session.commit()
    return redirect(url_for('economias'))

@app.route('/admin_painel')
@login_required
def admin_painel():
    if current_user.username != 'Milena': 
        return "<h1>Acesso Proibido</h1><p>Você não tem permissão de administrador.</p>", 403

    usuarios = User.query.order_by(User.id.desc()).all()
    total_gastos = Gasto.query.count()
    return render_template('admin.html', usuarios=usuarios, total_gastos=total_gastos)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)