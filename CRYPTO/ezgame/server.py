from Crypto.Util.number import getPrime, inverse, GCD
from hashlib import sha256, sha512
from secret import FLAG
import secrets
import socketserver
import signal

banner = r"""
 ██████   █████                      █████████  ███████████ ███████████
░░██████ ░░███                      ███░░░░░███░█░░░███░░░█░░███░░░░░░█
 ░███░███ ░███   ██████  ████████  ███     ░░░ ░   ░███  ░  ░███   █ ░ 
 ░███░░███░███  ███░░███░░███░░███░███             ░███     ░███████   
 ░███ ░░██████ ░███████  ░███ ░███░███             ░███     ░███░░░█   
 ░███  ░░█████ ░███░░░   ░███ ░███░░███     ███    ░███     ░███  ░    
 █████  ░░█████░░██████  ░███████  ░░█████████     █████    █████      
░░░░░    ░░░░░  ░░░░░░   ░███░░░    ░░░░░░░░░     ░░░░░    ░░░░░       
                         ░███                                          
                         █████                                         
                        ░░░░░                                          
  ████████     █████     ████████   ████████                           
 ███░░░░███  ███░░░███  ███░░░░███ ███░░░░███                          
░░░    ░███ ███   ░░███░░░    ░███░███   ░░░                           
   ███████ ░███    ░███   ███████ ░█████████                           
  ███░░░░  ░███    ░███  ███░░░░  ░███░░░░███                          
 ███      █░░███   ███  ███      █░███   ░███                          
░██████████ ░░░█████░  ░██████████░░████████                           
░░░░░░░░░░    ░░░░░░   ░░░░░░░░░░  ░░░░░░░░                            



"""

MBIT = 512
ROUNDS = 40
RSA_BITS = 1024
RSA_E = 65537
MAX_INPUT = 32
ROUND_RANDOM_BYTES = 16

ROCK, SCISSORS, PAPER = 0, 1, 2
MOVES = ("rock", "scissors", "paper")
MOVE_TO_ID = {name.encode(): i for i, name in enumerate(MOVES)}


def rand_nonzero_bits(bits: int) -> int:
    while True:
        x = secrets.randbits(bits)
        if x != 0:
            return x

def crt(residues, moduli) -> int:
    a1, a2 = residues
    m1, m2 = moduli
    return (a1 + m1 * (((a2 - a1) * inverse(m1, m2)) % m2)) % (m1 * m2)

def H(i: int, r: bytes) -> int:
    assert 0 <= i <= 2
    return int.from_bytes(sha512(bytes([i]) + r).digest(), "big")


class Commitment:
    def __init__(self, nbits: int = RSA_BITS, e: int = RSA_E):
        assert RSA_BITS % 2 == 0
        while True:
            p = getPrime(nbits // 2)
            q = getPrime(nbits // 2)
            if GCD(p - 1, e) == 1 and GCD(q - 1, e) == 1:
                break

        self.p, self.q, self.e = p, q, e
        self.n = p * q
        self.dp = inverse(e, p - 1)
        self.dq = inverse(e, q - 1)

    def parameters(self):
        return self.n, self.e

    def _sample_mask(self) -> int:
        while True:
            mask = rand_nonzero_bits(MBIT)
            if GCD(mask, self.n) == 1:
                return mask

    def commit(self, value: int):
        mask = self._sample_mask()
        return pow(mask, self.e, self.n), value ^ mask

    def _recover_mask(self, token: int) -> int:
        rp = pow(token, self.dp, self.p)
        rq = pow(token, self.dq, self.q)
        mask = crt((rp, rq), (self.p, self.q))
        assert pow(mask, self.e, self.n) == token
        return mask

    def open(self, commitment):
        token, masked = commitment
        return masked ^ self._recover_mask(token)


COM = Commitment()


class EZ_GAME(socketserver.BaseRequestHandler):
    def readline(self, prompt: bytes = b"") -> bytes:
        self.send(prompt, newline=False)
        data = b""
        while len(data) < MAX_INPUT:
            ch = self.request.recv(1)
            if not ch or ch in b"\r\n":
                break
            data += ch
        return data.strip()

    def send(self, msg: bytes, newline: bool = True):
        try:
            if newline:
                msg += b"\n"
            self.request.sendall(msg)
        except OSError:
            pass

    def proof_of_work(self) -> bool:
        table = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        proof = "".join(secrets.choice(table) for _ in range(20)).encode()
        digest = sha256(proof).hexdigest().encode()
        self.send(b"[+] sha256(XXX+" + proof[3:] + b") == " + digest)
        xxx = self.readline(b"[+] Plz Tell Me XXX: ")
        return len(xxx) == 3 and sha256(xxx + proof[3:]).hexdigest().encode() == digest

    @staticmethod
    def beats(player: int, dealer: int) -> bool:
        # rock beats scissors, scissors beats paper, paper beats rock
        return dealer == (player + 1) % 3

    def parse_move(self, data: bytes):
        return MOVE_TO_ID.get(data.strip().lower())

    def play_round(self, idx: int) -> bool:
        r = secrets.token_bytes(ROUND_RANDOM_BYTES)
        dealer = secrets.randbelow(3)
        commitment = COM.commit(H(dealer, r))

        self.send(f"[round {idx}/{ROUNDS}]".encode())
        self.send(f"r = {r.hex()}".encode())
        self.send(b"I have committed to my move. Now your turn.")
        self.send(f"commitment: {commitment}".encode())

        data = self.readline(b"your move [rock/scissors/paper]: ")
        player = self.parse_move(data)
        if player is None:
            self.send(b"Invalid move. Use rock, scissors, or paper.")
            return False

        self.send(f"I played {MOVES[dealer]}.".encode())
        self.send(f"You played {MOVES[player]}.".encode())
        return self.beats(player, dealer)

    def handle(self):
        signal.alarm(100)
        self.send(banner.encode("utf-8"))
        
        if not self.proof_of_work():
            self.request.close()
            return

        self.send(b"Welcome to NepCTF 2026")
        self.send(f"Beat me in RPS game for {ROUNDS} rounds.".encode())
        n, e = COM.parameters()
        self.send(f"parameters: n = {n}, e = {e}".encode())

        for i in range(1, ROUNDS + 1):
            if not self.play_round(i):
                self.send(b"You lose.")
                self.request.close()
                return
            self.send(b"You win this round.")

        self.send(b"You win the game!")
        self.send(b"flag: " + FLAG)
        self.request.close()


class ForkedServer(socketserver.ForkingMixIn, socketserver.TCPServer):
    allow_reuse_address = True


if __name__ == "__main__":
    HOST, PORT = "0.0.0.0", 10001
    print("HOST:PORT " + HOST + ":" + str(PORT), flush=True)
    with ForkedServer((HOST, PORT), EZ_GAME) as server:
        server.serve_forever()
