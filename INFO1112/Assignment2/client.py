import sys
import socket
import threading


client_socket = None
server_address = ()
most_recent_message = ""


def launch_check(args: list[str]) -> None:
    if len(args) != 2:
        sys.stderr.write(f"Error: Expecting 2 arguments: <server address> <port>\n")
        exit(1)
    global client_socket, server_address
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server_address = (args[0], int(args[1]))
        print(f"connecting to server {server_address}")
        client_socket.connect(server_address)
    except:
        sys.stderr.write(f"Error: cannot connect to server at <server address> and <port>.\n")
        exit(1)


def prompt_message():
    global client_socket, most_recent_message
    with client_socket:
        while True:
            try:
                message = input()
            except Exception as e:
                print(f"error prompting for message: {e}")
                exit(1)
            if message == "QUIT":
                exit(0)
            elif message == "LOGIN":
                message = prompt_login_protocol()
            elif message == "REGISTER":
                message = prompt_register_protocol()
            most_recent_message = message
            client_socket.sendall(message.encode())


def receive_data():
    global client_socket, server_address
    while True:
        try:
            data = client_socket.recv(8192)
            if not data:
                print(f"no data received")
                exit(0)
        except Exception as e:
            print(f"error receiving data: {e}")
            exit(1)
        data = data.decode()
        print(f"received from {server_address}: {data}")
        if data.split(":")[0] == "LOGIN":
            receive_login_protocol(data)
        elif data.split(":")[0] == "REGISTER":
            receive_register_protocol(data)


def prompt_login_protocol() -> str:
    username = input("Enter username: ")
    password = input("Enter password: ")
    return f"LOGIN:{username}:{password}"


def receive_login_protocol(data: str) -> None:
    # response of a recent LOGIN message
    global most_recent_message
    status = data.split(":")[2]
    if status == "3":
        print(f"wrong format LOGIN message")
        return
    _, username, _ = most_recent_message.split(":")
    if status == "0":
        print(f"Welcome {username}")
    elif status == "1":
        print(f"Error: User {username} not found")
    elif status == "2":
        print(f"Error: Wrong password for user {username}")


def prompt_register_protocol() -> str:
    username = input("Enter username: ")
    password = input("Enter password: ")
    return f"REGISTER:{username}:{password}"


def receive_register_protocol(data: str) -> None:
    global most_recent_message
    status = data.split(":")[2]
    if status == "2":
        print(f"wrong format REGISTER message")
        return
    _, username, _ = most_recent_message.split(":")
    if status == "0":
        print(f"Successfully created user account {username}")
    elif status == "1":
        print(f"Error: User {username} already exists")


def main(args: list[str]) -> None:
    launch_check(args)
    receive_thread = threading.Thread(target=receive_data)
    receive_thread.daemon = True
    receive_thread.start()
    prompt_message()


if __name__ == "__main__":
    main(sys.argv[1:])
