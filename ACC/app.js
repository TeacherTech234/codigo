// procura o "form" e coloca um ouvinte de evento (addEventListener) que vai rodar quando o formulário for enviado
//"async function" porque vai ter "await" lá no meio da requisição HTTP (perfil.html)
// (e) é o evento do formulário sendo enviado
document.querySelector("form").addEventListener("submit", async function (e) {
    e.preventDefault(); // cancela o comportamento padrão do formulário que seria recarregar a página / mandar dados

    // verifica se a URL atual tem "index.html", isso define se o "form" é login (true) ou cadastro (false)
    const isLogin = window.location.pathname.includes("index.html");
    const form = e.target; // guarda o próprio formulário que foi enviado, pra poder manipular depois

    //ternário (if(?) / else(:))
    const dados = isLogin ? { // condição
        // se a condição for verdadeira, login faz só esse objeto, usuário / senha
        NomeUsuario: document.getElementById("NomeUsuario").value,
        SenhaUsuario: document.getElementById("SenhaUsuario").value
    } : { // se a condição for falsa, faz esse objeto mais completo
        NomeUsuario: document.getElementById("NomeUsuario").value,
        SenhaUsuario: document.getElementById("SenhaUsuario").value,
        NomeCompleto: document.getElementById("NomeCompleto").value,
        Email: document.getElementById("Email").value
    };

    const url = isLogin ? "http://localhost:5000/login" : "http://localhost:5000/enviar"; // define a rota do servidor


    try {
        // faz a requisição HTTP
        // mas antes, espera a resposta vir antes de continuar
        const response = await fetch(url, {
            method: "POST", // manda um POST
            headers: { "Content-Type": "application/json" }, // diz pro servidor que vai enviar o JSON
            body: JSON.stringify(dados) // transforma o objeto "dados" em JSON com stringify
        });

        const resposta = await response.json(); // pega a resposta bruta e converte em um objeto JSON
        // se o servidor devolveu {"mensagem":"sucesso"}, agora resposta.mensagem funciona

        if (!response.ok) { // se o servidor respondeu com status de erro, usa mensagem do servidor se tiver, senão usa "Erro desconhecido"
            throw new Error(resposta.mensagem || 'Erro desconhecido');
        }

        alert(resposta.mensagem); // mostra a mensagem pro usuário

        if (resposta.status === "ok") { // se o servidor mandou status: "ok"
            if (isLogin) { // guarda os dados do usuário no localStorage e redireciona pra página home
                localStorage.setItem("UserData", JSON.stringify(resposta.dados));
                window.location.href = "perfil.html";
            } else {
                window.location.href = "index.html"; // // não precisa salvar nada, só joga o usuário de volta pro index
            }
        }
    } catch (error) { // se der erro em qualquer parte do try, mostra alert com a mensagem de erro
        alert(`Erro: ${error.message}`);
        if (!isLogin) { // Se for na tela de cadastro, dá um reset() no form
            form.reset();
        }
    }
});