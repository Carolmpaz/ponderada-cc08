"""
versao3.py - A4, Versão 3: semáforos com a ORDEM TROCADA no produtor.

Ponderada CC08 (Tato) - Caroline Moraes Paz (N = 5)

Igual à versão 2, exceto que o produtor faz wait(mutex) ANTES de wait(vazio).
Quando o buffer enche, o produtor dorme em `vazio` segurando o `mutex`; o
consumidor, para liberar uma posição, precisa do `mutex`. Um espera o outro
para sempre: deadlock.

Se o consumidor ficar 1 s esperando, a execução é encerrada e registrada como
travamento. O produtor fica preso, mas é uma thread daemon e não impede o
programa de terminar.

Como rodar:  python3 versao3.py
"""

import threading
import time

# ---------------------------------------------------------------------------
# Parâmetros e funções de execução e medição
# ---------------------------------------------------------------------------

# Tamanho do buffer circular (N = 3 + (D2 mod 5), com D2 = 7).
N = 5

# Quantidade de amostras geradas pelo produtor em cada execução.
TOTAL_AMOSTRAS = 20_000

# Tempo máximo (s) que o consumidor espera sem receber nada antes de
# declarar travamento.
TIMEOUT_TRAVAMENTO = 1.0

# Quantas vezes cada versão é executada.
EXECUCOES = 3


def calcular_metricas(recebidas, total=TOTAL_AMOSTRAS):
    """
    Calcula as métricas de uma execução a partir das amostras recebidas.

    Parâmetros:
        recebidas (list): amostras na ordem em que o consumidor as leu.
            Pode conter None, se o consumidor leu uma posição nunca escrita.
        total (int): quantidade de amostras que o produtor deveria entregar.

    Retorno:
        dict com as chaves:
            consumidas: quantas leituras o consumidor fez;
            perdidas:   amostras de 0 a total-1 que nunca chegaram ao consumidor;
            duplicadas: leituras repetidas de uma amostra que já tinha chegado;
            invalidas:  leituras de posições vazias (None).

    Funcionamento:
        Separa as leituras válidas (números de 0 a total-1), conta as
        amostras distintas e compara com o total esperado.
    """
    validas = [a for a in recebidas if a is not None and 0 <= a < total]
    distintas = set(validas)
    return {
        "consumidas": len(recebidas),
        "perdidas": total - len(distintas),
        "duplicadas": len(validas) - len(distintas),
        "invalidas": len(recebidas) - len(validas),
    }


def executar_uma(produtor, consumidor, estado):
    """
    Roda uma execução: dispara as threads produtora e consumidora.

    Parâmetros:
        produtor (callable): função produtor(estado) da versão.
        consumidor (callable): função consumidor(estado, recebidas) da versão,
            que devolve True se detectou travamento e False caso contrário.
        estado (object): estado compartilhado (buffer, contadores, semáforos).

    Retorno:
        tupla (recebidas, travou, duracao_em_segundos).

    Funcionamento:
        As threads são daemon: se o produtor ficar bloqueado para sempre
        (como no deadlock da versão 3), ele não impede o programa de terminar.
        A execução acaba quando o consumidor termina, normalmente ou por
        travamento.
    """
    recebidas = []
    resultado = {"travou": False}

    def alvo_consumidor():
        resultado["travou"] = consumidor(estado, recebidas)

    t_prod = threading.Thread(target=produtor, args=(estado,), daemon=True)
    t_cons = threading.Thread(target=alvo_consumidor, daemon=True)

    inicio = time.monotonic()
    t_prod.start()
    t_cons.start()
    t_cons.join()
    t_prod.join(timeout=0.5)
    duracao = time.monotonic() - inicio

    return recebidas, resultado["travou"], duracao


def executar_varias(nome, produtor, consumidor, criar_estado):
    """
    Roda a versão EXECUCOES vezes e imprime os resultados.

    Parâmetros:
        nome (str): nome da versão, usado nos títulos.
        produtor (callable): função produtora da versão.
        consumidor (callable): função consumidora da versão.
        criar_estado (callable): função sem parâmetros que devolve um estado
            novo e limpo para cada execução.

    Retorno:
        None. Imprime um resumo por execução e, no final, uma tabela em
        Markdown pronta para colar no ponderada-tato.md.
    """
    print(f"=== {nome} | N = {N} | {TOTAL_AMOSTRAS} amostras ===")
    linhas = []
    for i in range(1, EXECUCOES + 1):
        recebidas, travou, duracao = executar_uma(produtor, consumidor, criar_estado())
        m = calcular_metricas(recebidas)
        print(
            f"Execução {i}: consumidas={m['consumidas']} perdidas={m['perdidas']} "
            f"duplicadas={m['duplicadas']} inválidas={m['invalidas']} "
            f"travou={'SIM' if travou else 'não'} ({duracao:.2f} s)"
        )
        linhas.append((i, m, travou))

    print("\nTabela para o ponderada-tato.md:\n")
    print("| Execução | Consumidas | Perdidas | Duplicadas | Travou? |")
    print("|---|---|---|---|---|")
    for i, m, travou in linhas:
        print(
            f"| {i} | {m['consumidas']} | {m['perdidas']} | "
            f"{m['duplicadas']} | {'Sim' if travou else 'Não'} |"
        )


class EstadoV3:
    """
    Estado compartilhado protegido por semáforos (mesmo da versão 2).

    Atributos:
        buffer (list): N posições do buffer circular.
        entrada (int): próxima posição a ser escrita pelo produtor.
        saida (int): próxima posição a ser lida pelo consumidor.
        vazio (Semaphore): posições livres, valor inicial N.
        cheio (Semaphore): posições ocupadas, valor inicial 0.
        mutex (Semaphore): exclusão mútua, valor inicial 1.
    """

    def __init__(self):
        """Cria um estado vazio. Sem parâmetros; não retorna valor."""
        self.buffer = [None] * N
        self.entrada = 0
        self.saida = 0
        self.vazio = threading.Semaphore(N)
        self.cheio = threading.Semaphore(0)
        self.mutex = threading.Semaphore(1)


def produtor(estado):
    """
    Thread do sensor com a ordem errada dos waits.

    Parâmetros:
        estado (EstadoV3): estado compartilhado.

    Retorno:
        None (na prática, fica bloqueada para sempre quando o buffer enche).

    Funcionamento:
        Pega o mutex e só depois verifica se há posição livre. Com o buffer
        cheio, dorme em `vazio` sem soltar o mutex.
    """
    for amostra in range(TOTAL_AMOSTRAS):
        estado.mutex.acquire()               # wait(mutex)  <- ordem trocada
        estado.vazio.acquire()               # wait(vazio)  <- pode dormir com o mutex
        estado.buffer[estado.entrada] = amostra
        time.sleep(0)                        # interrupção no pior momento
        estado.entrada = (estado.entrada + 1) % N
        estado.mutex.release()               # signal(mutex)
        estado.cheio.release()               # signal(cheio)


def consumidor(estado, recebidas):
    """
    Thread do motor (idêntica à da versão 2).

    Parâmetros:
        estado (EstadoV3): estado compartilhado.
        recebidas (list): lista onde cada amostra lida é anotada.

    Retorno:
        bool: True se ficou TIMEOUT_TRAVAMENTO segundos esperando um semáforo
        (travamento), False se recebeu as TOTAL_AMOSTRAS amostras.

    Funcionamento:
        wait(cheio), wait(mutex), lê a amostra, signal(mutex), signal(vazio).
        No deadlock, fica preso em wait(mutex) e o timeout detecta.
    """
    while len(recebidas) < TOTAL_AMOSTRAS:
        if not estado.cheio.acquire(timeout=TIMEOUT_TRAVAMENTO):   # wait(cheio)
            return True
        if not estado.mutex.acquire(timeout=TIMEOUT_TRAVAMENTO):   # wait(mutex)
            return True
        amostra = estado.buffer[estado.saida]
        time.sleep(0)                        # interrupção no pior momento
        estado.saida = (estado.saida + 1) % N
        estado.mutex.release()               # signal(mutex)
        estado.vazio.release()               # signal(vazio)
        recebidas.append(amostra)
    return False


if __name__ == "__main__":
    executar_varias("Versão 3 (ordem trocada)", produtor, consumidor, EstadoV3)
