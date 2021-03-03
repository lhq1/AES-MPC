from player import *
import datetime
from threading import Thread

broadcast_time = datetime.datetime.now()
original_broadcast_time = broadcast_time
sbox_time = datetime.datetime.now()
original_sbox_time = sbox_time


# 也许会出现端口占用报错，最好使用比较大的端口号
def broadcast():
    global broadcast_time
    t0 = datetime.datetime.now()
    players = ComputePlayer.ComputeList
    #print(players[0].rec_port, players[1].rec_port)
    t1 = Thread(target=players[0].prep_rec, args=())
    t2 = Thread(target=players[1].send_num, args=(players[1].broadcast, players[0].ip, players[0].rec_port))
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    #print(players[0].rec_port, players[1].rec_port)
    t1 = Thread(target=players[1].prep_rec, args=())
    t2 = Thread(target=players[0].send_num, args=(players[0].broadcast, players[1].ip, players[1].rec_port))
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    t1 = datetime.datetime.now()
    broadcast_time += t1-t0
    #print('broadcast time', t1-t0)


def poly_multiple(players, constants, powers, data, num):
    if len(constants) != len(powers):
        raise RuntimeError("No equal size")
    if num.__class__.__name__ == 'int':
        num = axis_1D(num)

    for p in players:
        if data == 'plain':
            p.target = p.plains[num[0]][num[1]]
        else:
            p.target = p.keys[num[0]][num[1]]
        p.current_multiple = p.multiples.pop()
        p.set_global(p.target - p.current_multiple[0][0])
    broadcast()
    for p in players:
        res = p.poly_multiple_local(constants, powers, p.broadcast+p.other, p.current_multiple)
        if data == 'plain':
            p.plains[num[0]][num[1]] = res
        else:
            p.keys[num[0]][num[1]] = res


def sbox_multiple(players, data='plain', num=0):
    constants = [
        0x63, 0x8F, 0xB5, 0x01, 0xF4, 0x25, 0xF9, 0x09, 0x05
    ]
    powers = [
        0, 127, 191, 223, 239, 247, 251, 253, 254
    ]
    poly_multiple(players, constants, powers, data, num)


# method=0--multiple, method=1--beaver triple
def sbox(players, data='plain', num=(0,0), method=0):
    global sbox_time
    t0 = datetime.datetime.now()
    if method == 0:
        sbox_multiple(players, data, num)
    else:
        sbox_beaver_square(players, data, num)
    t1 = datetime.datetime.now()
    sbox_time += t1-t0


def sub_byte(players, method=0):
    for i in range(4):
        for j in range(4):
            sbox(players,'plain', (i,j), method)


def multiply_beaver(players):
    for p in players:
        p.current_beaver_triple = p.beaver_triples.pop()
        p.set_global(p.multiply_x - p.current_beaver_triple[0])
    t0 = datetime.datetime.now()
    broadcast()
    for p in players:
        p.delta = p.broadcast + p.other
        p.set_global(p.multiply_y - p.current_beaver_triple[1])
    broadcast()
    t1=datetime.datetime.now()
    #print('2 broadcast time', t1-t0)
    for p in players:
        p.epsilon = p.broadcast + p.other
        p.beaver_multiply_local(p.delta, p.epsilon, p.current_beaver_triple)


def generate_squares(players, degree=8):
    for p in players:
        p.current_square = p.squares.pop()
        p.set_global(p.multiply_x - p.current_square[0])
    broadcast()
    for p in players:
        p.set_multiply_x(p.broadcast + p.other)
        p.input_squares.append(p.multiply_x)
        for i in range(degree-1):
            p.input_squares.append(power(p.multiply_x, 2)+p.current_square[i])
            p.set_multiply_x(power(p.multiply_x, 2))


def multiply_beaver_wrap(players, data1='input_square', num1=0, data2='input_square', num2=0):
    for p in players:
        p.set_target(data1, num1)
        p.set_multiply_x(p.target)
        p.set_target(data2, num2)
        p.set_multiply_y(p.target)
    multiply_beaver(players)


def sbox_beaver_square(players, data='plain', num=(0, 0)):
    for p in players:
        p.set_target(data, num)
        p.set_multiply_x(p.target)
    generate_squares(players)

    multiply_beaver_wrap(players, num1=0, num2=1)
    for p in players:
        p.multiply_x_3 = p.product
        p.set_multiply_x(p.multiply_x_3)
        p.set_multiply_y(p.input_squares[2])
    multiply_beaver(players)
    for p in players:
        p.multiply_x_7 = p.product
        p.set_multiply_x(p.multiply_x_7)
        p.set_multiply_y(p.input_squares[3])
    multiply_beaver(players)
    for p in players:
        p.multiply_x_15 = p.product
        p.set_multiply_x(p.multiply_x_15)
        p.set_multiply_y(p.input_squares[4])
    multiply_beaver(players)
    for p in players:
        p.multiply_x_31 = p.product
        p.set_multiply_x(p.multiply_x_31)
        p.set_multiply_y(p.input_squares[5])
    multiply_beaver(players)
    for p in players:
        p.multiply_x_63 = p.product
        p.set_multiply_x(p.multiply_x_63)
        p.set_multiply_y(p.input_squares[6])
    multiply_beaver(players)
    for p in players:
        p.multiply_x_127 = p.product

    multiply_beaver_wrap(players, num1=7, num2=6)
    for p in players:
        p.multiply_x_192 = p.product
        p.set_multiply_x(p.multiply_x_192)
        p.set_multiply_y(p.input_squares[5])
    multiply_beaver(players)
    for p in players:
        p.multiply_x_224 = p.product
        p.set_multiply_x(p.multiply_x_224)
        p.set_multiply_y(p.input_squares[4])
    multiply_beaver(players)
    for p in players:
        p.multiply_x_240 = p.product
        p.set_multiply_x(p.multiply_x_240)
        p.set_multiply_y(p.input_squares[3])
    multiply_beaver(players)
    for p in players:
        p.multiply_x_248 = p.product
        p.set_multiply_x(p.multiply_x_248)
        p.set_multiply_y(p.input_squares[2])
    multiply_beaver(players)
    for p in players:
        p.multiply_x_252 = p.product
        p.set_multiply_x(p.multiply_x_252)
        p.set_multiply_y(p.input_squares[1])
    multiply_beaver(players)
    for p in players:
        p.multiply_x_254 = p.product

        p.set_multiply_x(p.input_squares[7])
        p.set_multiply_y(p.multiply_x_63)
    multiply_beaver(players)
    for p in players:
        p.multiply_x_191 = p.product
        p.set_multiply_x(p.multiply_x_192)
        p.set_multiply_y(p.multiply_x_31)
    multiply_beaver(players)
    for p in players:
        p.multiply_x_223 = p.product
        p.set_multiply_x(p.multiply_x_224)
        p.set_multiply_y(p.multiply_x_15)
    multiply_beaver(players)
    for p in players:
        p.multiply_x_239 = p.product
        p.set_multiply_x(p.multiply_x_240)
        p.set_multiply_y(p.multiply_x_7)
    multiply_beaver(players)
    for p in players:
        p.multiply_x_247 = p.product
        p.set_multiply_x(p.multiply_x_248)
        p.set_multiply_y(p.multiply_x_3)
    multiply_beaver(players)
    for p in players:
        p.multiply_x_251 = p.product
        p.set_multiply_x(p.multiply_x_252)
        p.set_multiply_y(p.input_squares[0])
    multiply_beaver(players)
    for p in players:
        p.multiply_x_253 = p.product
        p.powers = [GF256(1), p.multiply_x_127, p.multiply_x_191, p.multiply_x_223, p.multiply_x_239,
                    p.multiply_x_247,p.multiply_x_251, p.multiply_x_253, p.multiply_x_254]
    constants = [
        0x63, 0x8F, 0xB5, 0x01, 0xF4, 0x25, 0xF9, 0x09, 0x05
    ]
    for p in players:
        p.target = GF256(0)
        for i in range(9):
            p.target += GF256(constants[i]) * p.powers[i]
        if data == "plain":
            p.plains[num[0]][num[1]] = p.target
        else:
            p.keys[num[0]][num[1]] = p.target


def shift(lst, k):
  x = lst[:k]
  x.reverse()
  y = lst[k:]
  y.reverse()
  r = x+y
  return list(reversed(r))


def shift_row(players):
    offset = [0, 1, 2, 3]
    for p in players:
        for i in range(4):
            p.set_plain_row(shift(p.get_plain_row(i), offset[i]), i)


def matrix_multiplication(x, y):
    if len(x[0]) != len(y):
        raise RuntimeError("No valid shape")
    h, w, c = len(x), len(y[0]), len(y)
    res = [[] for _ in range(h)]
    for i in range(h):
        for j in range(w):
            temp = GF256(0)
            for k in range(c):
                temp += x[i][k] * y[k][j]
            res[i].append(temp)
    return res


def column_mixture(players):
    C = [[2, 3, 1, 1],
         [1, 2, 3, 1],
         [1, 1, 2, 3],
         [3, 1, 1, 2]]
    for i in range(4):
        for j in range(4):
            C[i][j] = GF256(C[i][j])
    for p in players:
        matrix_multiplication(C, p.plains)


def add_round_key(players):
    for p in players:
        for i in range(4):
            for j in range(4):
                p.plains[i][j] += p.keys[i][j]


def get_column(matrix, num, col_num=4):
    lis = []
    for i in range(col_num):
        lis.append(matrix[i][num])
    return lis


def key_expansion(players,method=0):
    for p in players:
        p.temp = []
        for i in range(4):
            p.temp.append(p.keys[3][i])
    for i in range(4):
        sbox(players, 'key', (3,i), method)
    for p in players:
        for i in range(4):
            p.keys[0][i] += p.keys[3][i]
        for col in range(1, 3):
            for i in range(4):
                p.keys[col][i] += p.keys[col-1][i]
        for i in range(4):
            p.keys[3][i] = p.temp[i] + p.keys[2][i]


def AES(players=ComputePlayer.ComputeList, method=0):
    add_round_key(players)
    for i in range(9):
        sub_byte(players, method)
        shift_row(players)
        column_mixture(players)
        key_expansion(players, method)
        add_round_key(players)
    sub_byte(players,method)
    column_mixture(players)
    key_expansion(players, method)
    add_round_key(players)


if __name__ == '__main__':
    t0 = datetime.datetime.now()
    a = InputTTP()
    mode = 0
    players = [ComputePlayer(rec_port=30000), ComputePlayer(rec_port=40000)]
    a.generate_plains([GF256(i) for i in range(16)])
    a.generate_keys([GF256(i) for i in range(16)])
    if mode == 0:
        a.generate_multiple(1, 254, 200)
    else:
        a.generate_beaver_triple(18*200)
        a.generate_squares(8, 200)
    st = datetime.datetime.now()
    AES(players,  method=mode)
    et = datetime.datetime.now()
    print('online time: ', et-st)
    print('broadcast_time', broadcast_time-original_broadcast_time)
    print('sbox time', sbox_time-original_sbox_time)
    print('offline time', st - t0)
