from gf256 import GF256
import socket
import random
from itertools import combinations, combinations_with_replacement
import functools

'''
接下来的改进地方：
1). 由于python GIL限制，无法充分发挥多线程的优势，考虑用更好的方式代替(比如多线程)
2). 使用更加快速的通讯方式(最好是异步的)
3). gmpy 优化
'''


# lis(16)->lis(4 * 4)
def reshape_16(lis):
    res = [[] for _ in range(4)]
    for i in range(4):
        for j in range(4):
            res[i].append(lis[4 * i + j])
    return res


def axis_1D(axis):
    return (axis//4, axis%4)


def comb(n, b):
    res = 1
    for i in range(n - b + 1, n + 1):
        res *= i
    for i in range(1, b + 1):
        res //= i
    return res


def power(x, n):
    mul = GF256(1)
    for _ in range(n):
        mul *= x
    return mul


dic_sbox = {}
dic_sbox_inv = {}
powers_sbox = [
        0, 127, 191, 223, 239, 247, 251, 253, 254
]
for i in range(255):
    for j in range(255):
        if (j, i) not in dic_sbox.keys():
            dic_sbox_inv[(j, i)] = comb(j, i)
            if j in powers_sbox:
                dic_sbox[(j,i)] = comb(j, i)


class Player():
    Num_player = 0

    def __init__(self,ip='localhost', rec_port=5000):
        self.no = Player.Num_player
        Player.Num_player += 1
        self.ip = ip
        self.rec_port = rec_port

    def send_num(self,number, target_ip, target_port):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((target_ip, target_port))
        s.send(str(int(number)).encode())
        s.close()

    def prep_rec(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("", self.rec_port))
        s.listen(1)
        self.conn, self.addr = s.accept()
        self.soc=s
        data = self.conn.recv(100).decode()
        data = GF256(int(data))
        self.conn.close()
        self.rec_port += 1
        self.other = data

    def calculate_share(self, inputs):
        shares = [[] for _ in range(ComputePlayer.ComputeNum)]
        for i in inputs:
            sum = GF256(0)
            for j in range(ComputePlayer.ComputeNum - 1):
                temp = GF256(random.randint(0, 255))
                shares[j].append(temp)
                sum += temp
            shares[ComputePlayer.ComputeNum-1].append(i - sum)
        return shares


class InputPlayer(Player):
    def __init__(self, ip='localhost', rec_port=5000):
        super().__init__(ip, rec_port)

    def generate_keys(self, inputs):
        shares = self.calculate_share(inputs)
        for i in range(ComputePlayer.ComputeNum):
            ComputePlayer.ComputeList[i].set_keys(shares[i])

    def generate_plains(self, inputs):
        shares = self.calculate_share(inputs)
        for i in range(ComputePlayer.ComputeNum):
            ComputePlayer.ComputeList[i].set_plains(shares[i])


class ComputePlayer(Player):
    ComputeNum = 0
    ComputeList = []

    def __init__(self, ip='localhost', rec_port=5000):
        super().__init__(ip, rec_port)
        self.others = ComputePlayer.ComputeList[:]
        for p in self.others:
            p.others.append(self)
        ComputePlayer.ComputeList.append(self)
        self.compute_no = ComputePlayer.ComputeNum
        ComputePlayer.ComputeNum += 1
        self.keys = []
        self.plains = []
        self.beaver_triples = []
        self.multiples = []
        self.squares = []
        self.input_squares = []
        self.broadcast = None
        self.multiply_x,self.multiply_y = None, None
        self.target = None
        self.powers_multiply = []

    def set_secrets(self, secrets):
        self.secrets = secrets[:]

    def set_keys(self, keys):
        self.keys = keys[:]
        self.keys = reshape_16(self.keys)

    def set_plains(self, plains):
        self.plains = plains[:]
        self.plains = reshape_16(self.plains)

    def set_plain_row(self, row, num):
        self.plains[num] = row

    def get_plain_row(self, num):
        return self.plains[num]

    def set_squares(self, squares):
        self.squares = squares[:]

    def set_beaver_triples(self, beaver_triples):
        self.beaver_triples = beaver_triples[:]

    def set_multiples(self, multiples):
        self.multiples = multiples[:]

    def set_global(self, broadcast):
        self.broadcast = broadcast

    # delta = x - a, epsilon = y-b, triple=[a],[b],[ab]
    def beaver_multiply_local(self, delta, epsilon, triple):
        a, b, c = triple
        if self.compute_no == 0:
            self.product = a * epsilon + b * delta + c + epsilon * delta
        else:
            self.product = a * epsilon + b * delta + c
        return self.product

    def set_multiply_x(self, value):
        self.multiply_x = value

    def set_multiply_y(self, value):
        self.multiply_y = value

    def set_target(self, data, num):
        if data == 'plain':
            self.target = self.plains[num[0]][num[1]]
        elif data == 'key':
            self.target = self.keys[num[0]][num[1]]
        elif data == 'square':
            self.target = self.squares[num]
        elif data == 'input_square':
            self.target = self.input_square[num]
        else:
            self.target = None


    def poly_multiple_local(self, constants, powers, global_z, multiple, mode='encode'):
        # calculate z^i
        z_powers = [global_z]
        for i in range(254):
            z_powers.append(z_powers[i] * global_z)
        # calculate coefficient(containing constant and combination)
        rank = [GF256(0)] * 255
        for i in range(255):
            for j in range(len(constants)):
                if powers[j] >= i:
                    if mode=='encode':
                        if dic_sbox[(powers[j], i)] % 2 == 1: # characteristic = 2
                        #rank[i] += GF256(constants[j]) * power(global_z, powers[j] - i)
                            rank[i] += GF256(constants[j]) * z_powers[powers[j] - i]
                    else:
                        if dic_sbox_inv[(powers[j], i)] % 2 == 1: # characteristic = 2
                        #rank[i] += GF256(constants[j]) * power(global_z, powers[j] - i)
                            rank[i] += GF256(constants[j]) * z_powers[powers[j] - i]
        res = rank[0]

        for i in range(1, 255):
            res += multiple[i-1][0] * rank[i]

        return res


class TrustedThirdPlayer(Player):
    def __init__(self, ip='localhost', rec_port=5000):
        super().__init__(ip, rec_port)

    def generate_multiple(self, number,  degree, repeat, method=0):
        all_shares = [[] for _ in range(ComputePlayer.ComputeNum)]
        for i in range(repeat):
            secures = []
            share_loop = [[] for _ in range(ComputePlayer.ComputeNum)]

            for j in range(number):
                secures.append(GF256(random.randint(0, 255)))
            tmp = secures
            for d in range(1, degree+1):
                if method == 0:
                    #res = [functools.reduce(lambda x, y: x*y, i) for i in combinations_with_replacement(secures, d)]
                    res = tmp
                    tmp = [x * y for x in tmp for y in secures]
                else:
                    res = [functools.reduce(lambda x, y: x*y, i) for i in combinations(secures, d)]
                res_share = self.calculate_share(res)
                for i in range(ComputePlayer.ComputeNum):
                    share_loop[i].append(res_share[i])
            for i in range(ComputePlayer.ComputeNum):
                all_shares[i].append(share_loop[i])
        for i in range(ComputePlayer.ComputeNum):
            ComputePlayer.ComputeList[i].set_multiples(all_shares[i])

    def generate_beaver_triple(self, number):
        all_shares = [[] for _ in range(ComputePlayer.ComputeNum)]
        for i in range(number):
            a, b = GF256(random.randint(0, 255)), GF256(random.randint(0, 255))
            c = a * b
            res = self.calculate_share([a,b,c])
            for j in range(ComputePlayer.ComputeNum):
                all_shares[j].append(res[j])
        for i in range(ComputePlayer.ComputeNum):
            ComputePlayer.ComputeList[i].set_beaver_triples(all_shares[i])

    def generate_squares(self, degree, repeat):
        all_shares = [[] for _ in range(ComputePlayer.ComputeNum)]
        for i in range(repeat):
            square_loop=[]
            square_loop.append(GF256(random.randint(0, 255)))
            for j in range(1, degree):
                square_loop.append(power(square_loop[j-1], 2))
            res = self.calculate_share(square_loop)
            for j in range(ComputePlayer.ComputeNum):
                all_shares[j].append(res[j])
        for i in range(ComputePlayer.ComputeNum):
            ComputePlayer.ComputeList[i].set_squares(all_shares[i])


class InputTTP(InputPlayer, TrustedThirdPlayer):
    def __init__(self,ip='localhost', rec_port=5000):
        super().__init__(ip, rec_port)


if __name__ == '__main__':
    a = InputTTP()
    players = [ComputePlayer(rec_port=5000), ComputePlayer(rec_port=6000)]
    times = 1
    a.generate_keys([GF256(i) for i in range(16)])
    a.generate_plains([GF256(i) for i in range(16)])
    a.generate_beaver_triple(18 * times)
    a.generate_multiple(1, 254, times)
