# Flask micro framework web:
# request pega dados que vêm na requisição
# jsonify devolve JSON formatado
# send_from_directory manda arquivo pro cliente
from flask import Flask, request, jsonify, send_from_directory
import mysql.connector # conecta com o mysql
from flask_cors import CORS # resolve o "erro" do CORS quando o front tenta acessar o back

import hashlib # gera hash (criptografia unidirecional)
import os # mexe com o sistema de arquivos (pastas, arquivos, etc)
import binascii # transforma bytes em hexadecimais legíveis
from werkzeug.utils import secure_filename # substitui o nome do arquivo (endereço) por um mais adequado (só o nome)
import shutil # manipula cópias de arquivos

UPLOAD_FOLDER = 'uploads' # pasta onde os arquivos vão

app = Flask(__name__) # inicia a aplicação Flask
CORS(app) # habilita CORS para todos

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER # registra a pasta no config do Flask
os.makedirs(UPLOAD_FOLDER, exist_ok=True) # cria a pasta uploads, se não existir

@app.route('/upload', methods=['POST']) # recebe arquivos via POST
def upload_arquivo(): # se não tiver arquivo, mostra o erro
    if 'arquivo' not in request.files:
        return jsonify({'mensagem': 'Nenhum arquivo enviado!', 'status': 'erro'}), 400

    file = request.files['arquivo'] # pega o arquivo enviado
    NomeUsuario = request.form.get('NomeUsuario') # pega o nome do usuário no formulário

    if file: # se o arquivo for válido, renomeia com o nome do usuario na frente do arquivo
        filename = secure_filename(f"{NomeUsuario}_{file.filename}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath) # salva, e retorna sucesso
        return jsonify({'mensagem': 'Upload concluído!', 'arquivo': filename, 'status': 'ok'})
    else: # senão ocorre erro
        return jsonify({'mensagem': 'Tipo de arquivo não permitido.', 'status': 'erro'}), 400
    
@app.route('/download/<filename>', methods=['GET']) # manda o arquivo solicitado pro cliente (forçando um download)
def download_arquivo(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@app.route('/listar_arquivos/<NomeUsuario>', methods=['GET']) # lista todos os arquivos que começam com o prefixo do usuário
def listar_arquivos(NomeUsuario):
    arquivos = [f for f in os.listdir(UPLOAD_FOLDER) if f.startswith(NomeUsuario + "_")]
    return jsonify({'arquivos': arquivos, 'status': 'ok'})

def generate_salt(): # cria uma sequencia aleatório (salt) de 16 bytes, pra dificultar um ataque
    return binascii.hexlify(os.urandom(16)).decode('utf-8')

def generate_salted_hash(password): # senha
    salt = generate_salt()
    salted_password = salt + password # junta o salt com a senha
    hashed_password = hashlib.sha256(salted_password.encode('utf-8')).hexdigest() # depois faz uma função hash SHA256 dessa mistura
    return f"{salt}:{hashed_password}" # no fim guarda

def verify_password(stored_password, provided_password): # verificação de senha, comparando hash gerado com o que já está salvo
    if not stored_password or ':' not in stored_password:
        return False
    salt, hashed_password = stored_password.split(':')
    new_hash = hashlib.sha256((salt + provided_password).encode('utf-8')).hexdigest()
    return new_hash == hashed_password

def conecta_db(): # conecta ao mysql
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="admin123",
        database="registro"
    )

@app.route('/enviar', methods=['POST']) # salvar dados
def salvar_dados():
    data = request.get_json()
    # verifica se o usuário já existe
    conn = conecta_db()
    cursor = conn.cursor()
    cursor.execute("SELECT NomeUsuario FROM informacoes WHERE NomeUsuario = %s", (data['NomeUsuario'],))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({ # mensagem de erro
            'mensagem': 'Nome de usuário já está em uso! Escolha outro.',
            'status': 'erro'
        }), 400
    
    # Criar hash seguro da senha
    hashed_password = generate_salted_hash(data['SenhaUsuario'])
    # Inserir novo usuário
    sql = """ -- insere no banco de dados com sql as informações
        INSERT INTO informacoes 
        (NomeUsuario, SenhaUsuario, NomeCompleto, Email)
        VALUES (%s, %s, %s, %s)
    """
    # recebe JSON com os dados do usuário
    valores = (
        data['NomeUsuario'],
        hashed_password,
        data['NomeCompleto'],
        data['Email']
    )
    try:
        cursor.execute(sql, valores)
        conn.commit()
        # copiar os arquivos padrão para o novo usuário
        copiar_arquivos_padrao(data['NomeUsuario'])
        return jsonify({ # mensagem de sucesso
            'mensagem': 'Cadastro realizado com sucesso!',
            'status': 'ok'
        })
    except Exception as e:
        return jsonify({ # mensagem de erro
            'mensagem': f'Erro ao cadastrar: {str(e)}',
            'status': 'erro'
        }), 500
    finally:
        cursor.close()
        conn.close()

def copiar_arquivos_padrao(nomeusuario): # copia os arquivos da pasta dos arquivos padrões e coloca um prefixo (usuário)
    pasta_padrao = 'arquivos_padrao'
    if os.path.exists(pasta_padrao):
        for arquivo in os.listdir(pasta_padrao):
            origem = os.path.join(pasta_padrao, arquivo)
            if os.path.isfile(origem):
                destino = os.path.join(app.config['UPLOAD_FOLDER'], f"{nomeusuario}_{arquivo}")
                shutil.copy2(origem, destino)

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json() # pega os dados do login que o cliente mandou no corpo da requisição
    nomeusuario = data['NomeUsuario']
    password = data['SenhaUsuario']

    conn = conecta_db() # vai no mysql e busca o usuário pelo nome de usuário
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM informacoes WHERE NomeUsuario = %s", (nomeusuario,)) # retorna todos os dados da tabela (inclusive a senha hash+salt)
    user = cursor.fetchone() # se não achar o que procura, não retorna nada
    cursor.close()
    conn.close()

    if user and verify_password(user['SenhaUsuario'], password): # checa se user existe e pega a senha digitada (password) e confere com o hash+salt armazenado
        user.pop('SenhaUsuario', None)  # tira a senha do dicionário do usuário antes de devolver
        return jsonify({ # mensagem de sucesso
            'mensagem': 'Login bem-sucedido!',
            'status': 'ok',
            'dados': user
        })
    else:
        return jsonify({ # mensagem de erro
            'mensagem': 'Usuário ou senha inválidos!',
            'status': 'erro'
        }), 401

@app.route('/deletar_conta', methods=['POST']) # apaga tudo relacionado ao usuário
def deletar_conta():
    data = request.get_json()
    nomeusuario = data.get('NomeUsuario')

    conn = conecta_db()
    cursor = conn.cursor()
    try:
        # apaga do banco de dados o usuário
        cursor.execute("DELETE FROM informacoes WHERE NomeUsuario = %s", (nomeusuario,))
        conn.commit()
        # apaga arquivos do usuário que foram salvos
        arquivos_usuario = [f for f in os.listdir(UPLOAD_FOLDER) if f.startswith(nomeusuario + "_")] # faz uma listagem e pega todos os arquivos que começam com o nome do usuário
        for arquivo in arquivos_usuario:
            try:
                os.remove(os.path.join(UPLOAD_FOLDER, arquivo)) # cada arquivo é apagado aqui
            except Exception as err: # mensagem de erro
                print(f"Erro ao deletar arquivo {arquivo}: {err}")
        # mensagem de sucesso
        return jsonify({'mensagem': 'Conta e arquivos deletados com sucesso.', 'status': 'ok'})
    except Exception as e: # mensagem de erro
        return jsonify({'mensagem': f'Erro ao deletar conta: {str(e)}', 'status': 'erro'}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/deletar_arquivo', methods=['POST'])
def deletar_arquivo(): # recebe nome do arquivo no JSON, e se existir deleta, senão, dá erro
    data = request.get_json()
    filename = data.get('filename')

    if not filename: # mensagem de erro
        return jsonify({'mensagem': 'Nome do arquivo não fornecido.', 'status': 'erro'}), 400

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    if os.path.exists(filepath):
        os.remove(filepath) 
        # mensagem de sucesso
        return jsonify({'mensagem': 'Arquivo deletado com sucesso.', 'status': 'ok'})
    else: # mensagem de erro
        return jsonify({'mensagem': 'Arquivo não encontrado.', 'status': 'erro'}), 404

@app.route('/resetar_arquivos', methods=['POST']) # resetar arquivos do usuário para o padrão
def resetar_arquivos():
    data = request.get_json()
    nomeusuario = data.get('NomeUsuario')

    if not nomeusuario: # mensagem de erro
        return jsonify({'mensagem': 'Usuário não especificado.', 'status': 'erro'}), 400
    try:
        # deleta os arquivos atuais do usuário
        arquivos_usuario = [f for f in os.listdir(UPLOAD_FOLDER) if f.startswith(nomeusuario + "_")]
        for arquivo in arquivos_usuario:
            try:
                os.remove(os.path.join(UPLOAD_FOLDER, arquivo))
            except Exception as err: # mensagem de erro
                print(f"Erro ao deletar arquivo {arquivo}: {err}")

        # Copia novamente os arquivos padrão na pasta
        copiar_arquivos_padrao(nomeusuario)
        # mensagem de sucesso
        return jsonify({'mensagem': 'Arquivos resetados com sucesso!', 'status': 'ok'})
    except Exception as e: # mensagem de erro
        return jsonify({'mensagem': f'Erro ao resetar arquivos: {str(e)}', 'status': 'erro'}), 500


@app.route('/trocar_senha', methods=['POST'])
def trocar_senha():
    data = request.get_json() # pega o JSON enviado no body da requisição e extrai do JSON o email e a NovaSenha
    email = data.get('Email')
    nova_senha = data.get('NovaSenha')

    # se faltar um dos dois manda erro
    if not email or not nova_senha:
        return jsonify({'mensagem': 'Email e nova senha são obrigatórios.', 'status': 'erro'}), 400
    # transforma a senha em hash antes de salvar
    hashed_password = generate_salted_hash(nova_senha)

    conn = conecta_db() # conecta no banco
    cursor = conn.cursor() # abre cursor pra executar SQL
    try:
        cursor.execute("UPDATE informacoes SET SenhaUsuario = %s WHERE Email = %s", (hashed_password, email)) # executa o UPDATE
        conn.commit() # confirma a transação
        
        # mensagens de erro / sucesso
        if cursor.rowcount == 0:
            return jsonify({'mensagem': 'E-mail não encontrado.', 'status': 'erro'}), 404
        return jsonify({'mensagem': 'Senha atualizada com sucesso!', 'status': 'ok'})
    # se der algum problema com o banco, mostra erro
    except Exception as e:
        return jsonify({'mensagem': f'Erro ao atualizar senha: {str(e)}', 'status': 'erro'}), 500
    finally:
        # fecha o cursor e a conexão
        cursor.close()
        conn.close()


@app.route('/trocar_nome', methods=['POST'])
def trocar_nome():
    data = request.get_json()  # pega o JSON enviado no body da requisição e extrai do JSON o email e o NovoNome
    email = data.get('Email')
    novo_nome = data.get('NovoNome')
    # se faltar um dos dois manda erro
    if not email or not novo_nome:
        return jsonify({'mensagem': 'Email e novo nome são obrigatórios.', 'status': 'erro'}), 400

    conn = conecta_db() # conecta no banco
    cursor = conn.cursor() # abre cursor pra executar SQL
    try:
        cursor.execute("UPDATE informacoes SET NomeCompleto = %s WHERE Email = %s", (novo_nome, email))
        conn.commit() # confirma a transação
        
        # mensagens de erro / sucesso
        if cursor.rowcount == 0:
            return jsonify({'mensagem': 'E-mail não encontrado.', 'status': 'erro'}), 404
        return jsonify({'mensagem': 'Nome atualizado com sucesso!', 'status': 'ok'})
    
    # se der algum problema com o banco, mostra erro
    except Exception as e:
        return jsonify({'mensagem': f'Erro ao atualizar nome: {str(e)}', 'status': 'erro'}), 500
    finally:
        # fecha o cursor e a conexão
        cursor.close()
        conn.close()


# roda a aplicação Flask 
if __name__ == '__main__':
    app.run(debug=True) # roda o modo debug (recarregamento automatico)