line1 = ['+', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '=']
line2 = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O',
         'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', 'a', 'b', 'c', 'd',
         'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's',
         't', 'u', 'v', 'w', 'x', 'y', 'z']

ref_value = 'MIICdwIBADANBgkqhkiG9w0BAQEFAASCAmEwggJdAgEAAoGBAMUwt5PUgUIj6/F33WuawCxFBeZEIBxeix2mPfR3x94qzFmvFPVrnXBI8aRAhY+CuWx6jPJ/jnQvQcsyHHyFFE6h9xe31R86WUMh2uq1Ny7wGU2wRIr6YlHjKAh5gDLzCL3XGzv72dv0clbOTUZHVGGFd5OX0KRk/Am0w+j8JKkzAgMBAAECgYB2Jq6YYSfh3WwuDsgZBWxIGkNiqUckOHHanhVZObwEHli7E/DW7Fg1Qz+mTxK33ngDy5pQYqWUcAxYF/qBkauMM9xNgwdc6JCjyztM6g0j81QHduQs+QPnRIYZDoPIc5HX0EVcwTjfH2tmQMvB7THFQuDerIMgLh/pRDd59hd5oQJBAPNdo3SJxnlvfMxjWq6naJnp1n9+E7lvo5qNNjpSnKCszo8vwpvML6hNiG0FFRKnyg8AM8QE09U/rvsw66Iz6B8CQQDPbWaaTutwOF5+x30Bq/os07vb3sVLh5RwNQgXnQxF7nDEP5ECqQnwVeYOjU4egrIVV0NeOnSu7GstxPcpKqxtAkArlofiJZMQyPEXQmxJf95yQrmSWCh8PAyXb9dYltdKx+ivKKS4dtfKUyiuLgzaLIc6LJUY9KxkM2XJw7dQc++NAkEAwG5u1FLIyugQii8JgoaIZhPb4ONvR121UM9x/W4d17aX+Qg7wCsP5F3cOr3OrjFzgqbdAcrbOvhrih+DaDaFlQJBAIkoJMeTMM8p8PJki3Yfsetvg/WewB71UOAdr0sJRi7w6hPjMFOgc+JJg78S/0NbFu49HgkmobNOGJpUhF3CjBk='

if __name__ == '__main__':
    trace = ''
    for e in ref_value:
        if e in line1:
            trace += '1'
        elif e in line2:
            trace += '2'

    print(trace)
