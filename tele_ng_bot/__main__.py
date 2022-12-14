from argparse import ArgumentParser
from .bot import tlbot, send_notification_to_allowed_ids
from tele_ng_bot.ngrok_wrapper import NgrokWrapper
from threading import Thread
from textwrap import dedent
from time import sleep
from requests import get

import logging


logging.getLogger("tele_ng_bot.ngrok_wrapper").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)
ngrok_client = NgrokWrapper()


def start_ngrok(http_ports: list[int] = [8000, 8080], tcp_ports: list[int] = [22]):
    ngrok_client.connect(
        tunnels={
            "http": http_ports,
            "tcp": tcp_ports
        }
    )
    ngrok_client.start()


def send_new_urls_notification():
    tunnels_data = ngrok_client.get_tunnels_links()
    message = ''
    for tunnel_data in tunnels_data:
        message += dedent(f'''
        name: {tunnel_data.get('name', None)}
        url: {tunnel_data.get('url', None)}
        addr: {tunnel_data.get('addr', None)}
        --------------------------------
        ''')

    send_notification_to_allowed_ids(message)


def get_tunnels_data():
    tunnels_data = []
    response = get(
        url='http://localhost:4040/api/tunnels',
        headers={
            'Accept': 'application/json',
        }
    )

    if 200 <= response.status_code < 300:
        tunnels = response.json().get('tunnels', [])
        for tunnel in tunnels:
            tunnels_data.append(
                {
                    'name': tunnel.get('name', None),
                    'url': tunnel.get('public_url', None),
                    'addr': tunnel.get('config', {}).get('addr')
                }
            )
    else:
        logger.warning(
            f'API responded with status code: {response.status_code}')

    return tunnels_data


def poll_ngrok_url_change():
    prev_urls = []
    while True:
        new_urls = [tunnel_data.get('url', None)
                    for tunnel_data in get_tunnels_data()]

        is_new_url = False
        for new_url in new_urls:
            if new_url not in prev_urls:
                is_new_url = True
                prev_urls.append(new_url)

        if is_new_url:
            send_new_urls_notification()

        sleep(20)


def main(http_ports: list[int], tcp_ports: list[int]):
    threads = []

    threads.append(Thread(target=start_ngrok, args=(http_ports, tcp_ports,)))
    threads.append(Thread(target=get_tunnels_data))
    threads.append(Thread(target=poll_ngrok_url_change))

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join(timeout=1.0)

    tlbot.infinity_polling()


if __name__ == '__main__':

    parser = ArgumentParser(
        prog='tele_bot_ng',
    )

    parser.add_argument('--http', dest='http_ports',default=[8000], nargs='+', type=int, help='web services ports separated by spaces')
    parser.add_argument('--tcp', dest='tcp_ports',default=[], nargs='+', type=int, help='tcp services ports separated by spaces')

    args = parser.parse_args()

    main(
        http_ports=args.http_ports,
        tcp_ports=args.tcp_ports
    )
