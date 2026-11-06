"""
versao1.py - A4, Versão 1: buffer circular SEM sincronização.

Ponderada CC08 (Tato) - Caroline Moraes Paz (N = 5)

O produtor (sensor) e o consumidor (motor) usam um contador compartilhado de
posições ocupadas e espera ocupada. Entre ler e escrever o contador há um
time.sleep(0), que libera a CPU e simula a thread sendo interrompida no pior
momento. Isso expõe a condição de corrida: atualizações do contador se perdem,
e o buffer passa a ser lido ou escrito na hora errada.

Se o consumidor ficar 1 s sem receber nada, a execução é encerrada e
registrada como travamento.

Como rodar:  python3 versao1.py
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


class EstadoV1:
    """
    Estado compartilhado entre as threads, sem nenhuma proteção.

    Atributos:
        buffer (list): N posições; None indica posição nunca escrita.
        contador (int): posições ocupadas, segundo as threads (região crítica).
        entrada (int): próxima posição a ser escrita pelo produtor.
        saida (int): próxima posição a ser lida pelo consumidor.
        produtor_terminou (bool): o produtor já gerou todas as amostras.
        encerrar (bool): pedido do consumidor para o produtor parar.
    """

    def __init__(self):
        """Cria um estado vazio. Sem parâmetros; não retorna valor."""
        self.buffer = [None] * N
        self.contador = 0
        self.entrada = 0
        self.saida = 0
        self.produtor_terminou = False
        self.encerrar = False


def produtor(estado):
    """
    Thread do sensor: gera as amostras 0, 1, 2, ... e as coloca no buffer.

    Parâmetros:
        estado (EstadoV1): estado compartilhado.

    Retorno:
        None.

    Funcionamento:
        Espera (ocupada) enquanto o contador indica buffer cheio, escreve a
        amostra e incrementa o contador em dois passos (ler, ceder a CPU,
        escrever). Se o consumidor pedir para encerrar, para imediatamente.
    """
    for amostra in range(TOTAL_AMOSTRAS):
        while estado.contador >= N:          # espera ocupada: buffer "cheio"
            if estado.encerrar:
                return
            time.sleep(0)
        estado.buffer[estado.entrada] = amostra
        estado.entrada = (estado.entrada + 1) % N

        valor = estado.contador              # REGIÃO CRÍTICA: ler...
        time.sleep(0)                        # ...ser interrompido...
        estado.contador = valor + 1          # ...escrever valor velho + 1
    estado.produtor_terminou = True


def consumidor(estado, recebidas):
    """
    Thread do motor: retira amostras do buffer e registra em `recebidas`.

    Parâmetros:
        estado (EstadoV1): estado compartilhado.
        recebidas (list): lista onde cada amostra lida é anotada.

    Retorno:
        bool: True se ficou TIMEOUT_TRAVAMENTO segundos sem receber nada
        (travamento), False se terminou normalmente.

    Funcionamento:
        Espera (ocupada) enquanto o contador indica buffer vazio. Termina
        quando o produtor já acabou e o contador indica que não há mais nada.
        Decrementa o contador com a mesma janela de corrida do produtor.
    """
    ultimo_recebimento = time.monotonic()
    while True:
        while estado.contador <= 0:          # espera ocupada: buffer "vazio"
            if estado.produtor_terminou:
                return False
            if time.monotonic() - ultimo_recebimento > TIMEOUT_TRAVAMENTO:
                estado.encerrar = True
                return True
            time.sleep(0)
        amostra = estado.buffer[estado.saida]
        estado.saida = (estado.saida + 1) % N
        recebidas.append(amostra)
        ultimo_recebimento = time.monotonic()

        valor = estado.contador              # REGIÃO CRÍTICA: ler...
        time.sleep(0)                        # ...ser interrompido...
        estado.contador = valor - 1          # ...escrever valor velho - 1


if __name__ == "__main__":
    executar_varias("Versão 1 (sem sincronização)", produtor, consumidor, EstadoV1)
