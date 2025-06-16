import asyncio
import socket
import time


class Channel:
    NUM_SAVED_RESPONSE_TIMES = 20

    def __init__(self, channel, host, port):
        self.channel = channel
        self.host = host
        self.port = port
        self.response_times = []

    def __str__(self):
        return str([self.channel, self.average_response_time()])

    def __repr__(self):
        return self.__str__()

    def check_ping_tcp(self, timeout=1):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # TCP
        sock.settimeout(timeout)
        try:
            start = time.time()
            sock.connect((self.host, self.port))
            sock.recv(1024)
            sock.close()
            end = time.time()
            self.__add_response_time(end - start)
        except:
            self.__add_response_time(-1)

    def check_ping_udp(self, timeout=1):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP
        sock.settimeout(timeout)

        # Ping to server
        message = b'test'

        addr = (self.host, self.port)

        # Send ping
        start = time.time()
        sock.sendto(message, addr)

        try:
            # If data is received back from server, print
            data, server = sock.recvfrom(1024)
            end = time.time()
            elapsed = end - start
            print(f'{data} {elapsed}')

        except timeout:
            # If data is not received back from server, print it has timed out
            print('REQUEST TIMED OUT')
        except:
            print('Other error')

    def __add_response_time(self, response_time):
        if len(self.response_times) > Channel.NUM_SAVED_RESPONSE_TIMES:
            self.response_times.pop(0)
        self.response_times.append(response_time)

    def average_response_time(self):
        return sum(self.response_times)


channels = [
    Channel(1, '35.155.204.207', 8585),
    Channel(2, '52.26.82.74', 8585),
    Channel(3, '34.217.205.66', 8585),
    Channel(4, '35.161.183.101', 8585),
    Channel(5, '54.218.157.183', 8585),
    Channel(6, '52.25.78.39', 8585),
    Channel(7, '54.68.160.34', 8585),
    Channel(8, '34.218.141.142', 8585),
    Channel(9, '52.33.249.126', 8585),
    Channel(10, '54.148.170.23', 8585),
    Channel(11, '54.201.184.26', 8585),
    Channel(12, '54.191.142.56', 8585),
    Channel(13, '52.13.185.207', 8585),
    Channel(14, '34.215.228.37', 8585),
    Channel(15, '54.187.177.143', 8585),
    Channel(16, '54.203.83.148', 8585),
    Channel(17, '54.148.188.235', 8585),
    Channel(18, '52.43.83.76', 8585),
    Channel(19, '54.69.114.137', 8585),
    Channel(20, '54.148.137.49', 8585),
    Channel(21, '54.212.109.33', 8585),
    Channel(22, '44.230.255.51', 8585),
    Channel(23, '100.20.116.83', 8585),
    Channel(24, '54.188.84.22', 8585),
    Channel(25, '34.215.170.50', 8585),
    Channel(26, '54.184.162.28', 8585),
    Channel(27, '54.185.209.29', 8585),
    Channel(28, '52.12.53.225', 8585),
    Channel(29, '54.189.33.238', 8585),
    Channel(30, '54.188.84.238', 8585),
    Channel(31, '44.234.162.14', 8585),
    Channel(32, '44.234.162.13', 8585),
    Channel(33, '44.234.161.92', 8585),
    Channel(34, '44.234.161.48', 8585),
    Channel(35, '44.234.160.137', 8585),
    Channel(36, '44.234.161.28', 8585),
    Channel(37, '44.234.162.100', 8585),
    Channel(38, '44.234.161.69', 8585),
    Channel(39, '44.234.162.145', 8585),
    Channel(40, '44.234.162.130', 8585)]


async def check_channels_ping():
    for channel in channels:
        asyncio.get_event_loop().run_in_executor(None, channel.check_ping_tcp)


def get_fatal_channel():
    def sum_response_times(channel):
        return sum(channel.response_times)

    def sum_totals(channel):
        return sum(channel.totals)

    # sorted_channels_by_total = sorted(channels, key=sum_totals)
    # print(
    #     f'Fastest: {sorted_channels_by_total[0]} {sorted_channels_by_total[1]} {sorted_channels_by_total[2]} {sorted_channels_by_total[3]} {sorted_channels_by_total[4]}')
    # print(
    #     f'Slowest: {sorted_channels_by_total[-1]} {sorted_channels_by_total[-2]} {sorted_channels_by_total[-3]} {sorted_channels_by_total[-4]} {sorted_channels_by_total[-5]}')

    sorted_channels_by_response_times = sorted(channels, key=sum_response_times)
    print(
        f'Fastest: {sorted_channels_by_response_times[0]} {sorted_channels_by_response_times[1]} {sorted_channels_by_response_times[2]} {sorted_channels_by_response_times[3]} {sorted_channels_by_response_times[4]}')
    print(
        f'Slowest: {sorted_channels_by_response_times[-1]} {sorted_channels_by_response_times[-2]} {sorted_channels_by_response_times[-3]} {sorted_channels_by_response_times[-4]} {sorted_channels_by_response_times[-5]}')


async def looper():
    while True:
        asyncio.create_task(check_channels_ping())
        await asyncio.sleep(5)
        get_fatal_channel()


asyncio.get_event_loop().run_until_complete(looper())
