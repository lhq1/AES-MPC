from gf256 import GF256
import socket
import random
from itertools import combinations, combinations_with_replacement
import functools

# lis(16)->lis(4 * 4)
def reshape_16(lis):
    res = [[] for _ in range(4)]
    for i in range(4):
        for j in range(4):
            res[i].append(lis[4 * i + j])
    return res


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


def generate_comb_eff(powers):
    comb_dic = set()
    for i in powers:
        for j in range(i):
            if comb(i,j) % 2:
                comb_dic.add((j,i))
    return comb_dic


def gen_rand_gf256():
    return GF256(random.randint(0, 255))


class Player():
    Num_player = 0

    def __init__(self,ip='localhost', rec_port=5000):
        self.no = Player.Num_player
        Player.Num_player += 1
        self.ip = ip
        self.rec_port = rec_port

    def send_num(self,lis, target_ip, target_port):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((target_ip, target_port))
        lis = [int(i) for i in lis]
        s.send(str(lis).encode())
        s.close()

    def prep_rec(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("", self.rec_port))
        s.listen(1)
        self.conn, self.addr = s.accept()
        self.soc=s
        data = self.conn.recv(10000).decode()
        data = [GF256(i) for i in eval(data)]
        self.conn.close()
        self.rec_port += 1
        self.other = data

    # this function is used by input_player and trusted_third_player
    # input-- inputs: list
    # output -- shares : two-dim list(first-dim:player, second-dim: additive secret sharing)
    def calculate_share(self, inputs):
        shares = [[] for _ in range(ComputePlayer.ComputeNum)]
        for i in inputs:
            sum = GF256(0)
            for j in range(ComputePlayer.ComputeNum - 1):
                temp = gen_rand_gf256()
                shares[j].append(temp)
                sum += temp
            shares[ComputePlayer.ComputeNum-1].append(i - sum)
        return shares

    def calculate_share_mac(self, inputs):
        shares = [[] for _ in range(ComputePlayer.ComputeNum)]
        for i in inputs:
            sum1 = GF256(0)
            sum2 = GF256(0)
            for j in range(ComputePlayer.ComputeNum - 1):
                temp1 = gen_rand_gf256()
                temp2 = gen_rand_gf256()
                shares[j].append((temp1, temp2))
                sum1 += temp1
                sum2 += temp2
            shares[ComputePlayer.ComputeNum-1].append((i[0] - sum1, i[1]-sum2))
        return shares


class InputPlayer(Player):
    def __init__(self, ip='localhost', rec_port=5000):
        super().__init__(ip, rec_port)

    def generate_keys(self, inputs, storage='memory'):
        shares = self.calculate_share(inputs)
        if storage == 'memory':
            for i in range(ComputePlayer.ComputeNum):
                ComputePlayer.ComputeList[i].set_keys(shares[i])
        elif storage == 'file':
            for i in range(ComputePlayer.ComputeNum):
                with open('key_P{}.txt'.format(i), 'w') as file:
                    print(len(shares[i]))
                    file.write(str(len(shares[i])))
                    file.write('\n')
                    for j in shares[i]:
                        file.write(str(j))
                        file.write('\n')

    # encode plain_text
    # decode cipher_text
    def generate_texts(self, inputs, storage='memory'):
        shares = self.calculate_share(inputs)
        if storage == 'memory':
            for i in range(ComputePlayer.ComputeNum):
                ComputePlayer.ComputeList[i].set_texts(shares[i])
        elif storage == 'file':
            for i in range(ComputePlayer.ComputeNum):
                with open('text_P{}.txt'.format(i), 'w') as file:
                    print(len(shares[i]))
                    file.write(str(len(shares[i])))
                    file.write('\n')
                    for j in shares[i]:
                        file.write(str(j))
                        file.write('\n')


class ComputePlayer(Player):
    ComputeNum = 0
    ComputeList = []
    TTP = None

    def __init__(self, ttp, ip='localhost', rec_port=5000):
        super().__init__(ip, rec_port)
        self.others = ComputePlayer.ComputeList[:]
        for p in self.others:
            p.others.append(self)
        ComputePlayer.ComputeList.append(self)
        self.compute_no = ComputePlayer.ComputeNum
        ComputePlayer.ComputeNum += 1
        ComputePlayer.TTP = ttp
        self.keys = []
        self.texts = []
        self.shares = []
        self.beaver_triples = []
        self.multiples = []
        self.squares = []
        self.input_square = []
        self.shares = []

    def set_shares(self, shares):
        self.shares.extend(shares)

    def set_keys(self, keys):
        self.keys = keys[:]
        self.keys = reshape_16(self.keys)

    def set_texts(self, keys):
        self.texts = keys[:]
        self.texts = reshape_16(self.texts)

    def set_beaver_triples(self, beavers):
        self.beaver_triples.extend(beavers)

    def set_squares(self, squares):
        self.squares = squares[:]

    def set_multiples(self, multiples):
        self.multiples = multiples[:]

    def generate_mac(self, method='memory'):
        self.mac = gen_rand_gf256()

        if method == 'memory':
            ComputePlayer.TTP.calculate_mac_sum(self.mac)
        elif method == 'file':
            with open('mac_P{}.txt'.format(self.compute_no), 'w') as file:
                file.write(str(self.mac))

    def beaver_multiply_local(self, multiply_x_mask, multiply_y_mask, triple):
        a, b, c = triple

        if self.compute_no == 0:
            temp1 = a[0] * multiply_y_mask + b[0] * multiply_x_mask + c[0] + multiply_y_mask * multiply_x_mask
        else:
            temp1 = a[0] * multiply_y_mask + b[0] * multiply_x_mask + c[0]
        temp2 = a[1] * multiply_y_mask + b[1] * multiply_x_mask + c[1] + multiply_y_mask * multiply_x_mask*self.mac
        product = (temp1, temp2)
        return product

    # multiply_mask -- (x1-a1, y1-b1,x2-a2,y2-b2,...)
    # triple -- (([a1],[b1],[c1]), ([a2],[b2],[c2]), ...)
    def beaver_multiply_parallel(self, multiply_mask,  triple):
        assert (2 * len(triple) == len(multiply_mask))
        res = []
        for i in range(len(triple)):
            product = self.beaver_multiply_local(multiply_mask[2 * i], multiply_mask[2* i + 1], triple[i])
            res.append(product)
        return res

    def set_multiply_mask(self, value):
        self.multiply_multiply_mask = value[:]

class TrustedThirdPlayer(Player):
    def __init__(self, ip='localhost', rec_port=5000):
        super().__init__(ip, rec_port)
        self.mac_sum = GF256(0)

    def calculate_mac_sum(self, value):
        if type(value) == GF256:
            self.mac_sum+= value
        else:
            with open(value, 'r') as file:
                self.mac_sum += GF256(int(file.readline()))

    def generate_mac_share(self, number, method='memory'):
        all_shares = [[] for _ in range(ComputePlayer.ComputeNum)]
        for i in range(number):
            num = gen_rand_gf256()
            mac_num = num * self.mac_sum
            temp = (num, mac_num)
            shares = self.calculate_share(temp)

            for j in range(ComputePlayer.ComputeNum):
                all_shares[j].append(tuple(shares[j]))
        if method == 'memory':
            for i in range(ComputePlayer.ComputeNum):
                ComputePlayer.ComputeList[i].set_shares(all_shares[i])
        elif method == 'file':
            for i in range(ComputePlayer.ComputeNum):
                with open('mac_share_P{}.txt'.format(i), 'w') as file:
                    print(len(all_shares[i]))
                    file.write(str(len(all_shares[i])))
                    file.write('\n')
                    for j in all_shares[i]:
                        file.write(str(j))
                        file.write('\n')
        else:
            return all_shares

    def generate_squares(self, degree, repeat, storage='memory'):
        all_shares = [[] for _ in range(ComputePlayer.ComputeNum)]
        for i in range(repeat):
            square_loop = []
            temp = gen_rand_gf256()
            mac_num = temp * self.mac_sum
            square_loop.append((temp, mac_num))
            for j in range(1, degree):
                temp = square_loop[j-1][0] * square_loop[j-1][0]
                mac_num = temp * self.mac_sum
                square_loop.append((temp, mac_num))
            res = self.calculate_share_mac(square_loop)
            for j in range(ComputePlayer.ComputeNum):
                all_shares[j].append(res[j])
        if storage == 'memory':
            for i in range(ComputePlayer.ComputeNum):
                ComputePlayer.ComputeList[i].set_squares(all_shares[i])
        elif storage == 'file':
            for i in range(ComputePlayer.ComputeNum):
                with open('square_P{}.txt'.format(i), 'w') as file:
                    print(len(all_shares[i]))
                    file.write(str(len(all_shares[i])))
                    file.write('\n')
                    for j in all_shares[i]:
                        file.write(str(j))
                        file.write('\n')

    def generate_beaver_triples(self, number, method='memory'):
        all_shares = [[] for _ in range(ComputePlayer.ComputeNum)]
        for i in range(number):
            a = gen_rand_gf256()
            b = gen_rand_gf256()
            c = a * b
            temp = (a, b, c, a * self.mac_sum, b*self.mac_sum, c*self.mac_sum)
            shares = self.calculate_share(temp)

            for j in range(ComputePlayer.ComputeNum):
                beaver_mac = tuple((shares[j][k], shares[j][k+3]) for k in range(3))
                all_shares[j].append(beaver_mac)
                #all_shares[j].append(tuple(shares[j][:3]))
        if method == 'memory':
            for i in range(ComputePlayer.ComputeNum):
                ComputePlayer.ComputeList[i].set_beaver_triples(all_shares[i])
        elif method == 'file':
            for i in range(ComputePlayer.ComputeNum):
                with open('beaver_triple_P{}.txt'.format(i), 'w') as file:
                    print(len(all_shares[i]))
                    file.write(str(len(all_shares[i])))
                    file.write('\n')
                    for j in all_shares[i]:
                        file.write(str(j))
                        file.write('\n')

    # method 0 --  repeat eg, (x,y,z) ->(x^2, y^2, ...)
    # method 1 --  no repeat eg,(x,y,z)-> (xy,yz,xz,xyz)
    def generate_multiple(self, number,  degree, repeat, method=0, storage='memory'):
        all_shares = [[] for _ in range(ComputePlayer.ComputeNum)]
        for i in range(repeat):
            secures = []
            share_loop = [[] for _ in range(ComputePlayer.ComputeNum)]

            for j in range(number):
                secures.append(gen_rand_gf256())
            res = secures
            for d in range(1, degree+1):
                if method == 0:
                    #res = [functools.reduce(lambda x, y: x*y, i) for i in combinations_with_replacement(secures, d)]
                    res = [x * y for x in res for y in secures]
                else:
                    res = [functools.reduce(lambda x, y: x*y, i) for i in combinations(secures, d)]
                res_share = self.calculate_share(res)
                for i in range(ComputePlayer.ComputeNum):
                    share_loop[i].append(res_share[i])
            for i in range(ComputePlayer.ComputeNum):
                all_shares[i].append(share_loop[i])
        if storage == 'memory':
            for i in range(ComputePlayer.ComputeNum):
                ComputePlayer.ComputeList[i].set_multiples(all_shares[i])
        elif storage == 'file':
            for i in range(ComputePlayer.ComputeNum):
                with open('multiple_P{}.txt'.format(i), 'w') as file:
                    file.write(str(len(all_shares[i])))
                    file.write('\n')
                    for j in all_shares[i]:
                        file.write(str(j))
                        file.write('\n')


class inputTTP(InputPlayer, TrustedThirdPlayer):
    def __init__(self, ip='localhost', rec_port=5000):
        super().__init__(ip, rec_port)


if __name__ == '__main__':
    #print(generate_comb_eff([i for i in range(255)]))
    #print(generate_comb_eff([0, 127, 191, 223, 239, 247, 251, 253, 254]))
    a = TrustedThirdPlayer(rec_port=4000)
    players = [ComputePlayer(a, rec_port=5000), ComputePlayer(a, rec_port=6000)]
    for p in players:
        p.generate_mac()
    a.generate_squares(8, 1)
    a.generate_beaver_triples(10)
    a.generate_multiple(1, 254, 1, storage='file')
    multiply_mask = [gen_rand_gf256() for i in range(20)]
    print(players[0].beaver_multiply_parallel(multiply_mask, players[0].beaver_triples))
