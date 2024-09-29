import sys
import socket
import select
import os
import json
import bcrypt


server_port = 0
user_database_path = ""
user_database = []
existing_username = set()


def config(args: list[str]) -> None:
    if len(args) != 1:
        sys.stderr.write(f"Error: Expecting 1 argument: <server config path>.\n")
        exit(1)
    server_config_path = args[0]
    server_config_path = os.path.expanduser(server_config_path)
    server_config_path = os.path.abspath(server_config_path)
    if not os.path.exists(server_config_path):
        sys.stderr.write(f"Error: <server config path> doesn't exist.\n")
        exit(1)
    try:
        with open(server_config_path) as fileobj:
            data = json.load(fileobj)
    except json.decoder.JSONDecodeError:
        sys.stderr.write(f"Error: <server config path> is not in a valid JSON format.\n")
        exit(1)
    missing_key = []
    if "port" not in data.keys():
        missing_key.append("port")
    if "userDatabase" not in data.keys():
        missing_key.append("userDatabase")
    if len(missing_key) > 0:
        sys.stderr.write(f"Error: <server config path> missing key(s): ")
        for i in range(len(missing_key)):
            sys.stderr.write(missing_key[i])
            if i < len(missing_key)-1:
                sys.stderr.write(", ")
        sys.stderr.write("\n")
        exit(1)
    
    global server_port, user_database_path
    server_port = data["port"]
    user_database_path = data["userDatabase"]
    user_database_path = os.path.expanduser(user_database_path)
    user_database_path = os.path.abspath(user_database_path)
    if not os.path.exists(user_database_path):
        sys.stderr.write(f"Error: <user database path> doesn't exist.\n")
        exit(1)
    try:
        with open(user_database_path) as fileobj:
            data = json.load(fileobj)
    except json.decoder.JSONDecodeError:
        sys.stderr.write(f"Error: <user database path> is not in a valid JSON format.\n")
        exit(1)
    if not isinstance(data, list):
        sys.stderr.write(f"Error: <user database path> is not a JSON array.\n")
        exit(1)
    for account in data:
        keys = sorted(account.keys())
        if keys != ["password", "username"]:
            sys.stderr.write(f"Error: <user database path> contains invalid user record formats.\n")
            exit(1)

    global user_database, existing_username
    user_database = data
    for user in user_database:
        existing_username.add(user["username"])


def create_client_socket(server_socket: socket.socket) -> None:
    client_socket, client_address = server_socket.accept()
    client_socket.setblocking(False)
    global sockets_list, clients
    sockets_list.append(client_socket)
    clients[client_socket] = client_address
    print(f"new connection from {client_address}")


def remove_client_socket(client_socket: socket.socket) -> None:
    global sockets_list, clients, auth_clients
    print(f"disconnection from {clients[client_socket]}")
    sockets_list.remove(client_socket)
    del clients[client_socket]
    auth_clients.discard(client_socket)


def login_protocol(client_socket: socket.socket, data: str) -> None:
    global auth_clients
    data = data.split(":")
    if len(data) != 3:
        client_socket.sendall("LOGIN:ACKSTATUS:3".encode())
        return
    _, username, password = data
    for user in user_database:
        if user["username"] != username:
            continue
        if bcrypt.checkpw(password.encode(), user["password"].encode()):
            client_socket.sendall("LOGIN:ACKSTATUS:0".encode())
            auth_clients.add(client_socket)
            return
        else:
            client_socket.sendall("LOGIN:ACKSTATUS:2".encode())
            return
    # username not found in user database
    client_socket.sendall("LOGIN:ACKSTATUS:1".encode())


def create_user_record(username: str, password: str) -> None:
    global user_database_path, user_database, existing_username
    user_record = {"username":username, "password":bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()}
    user_database.append(user_record)
    existing_username.add(username)
    with open(user_database_path, "w") as f:
        f.write("[\n")
        for i in range(len(user_database)):
            username = user_database[i]["username"]
            password = user_database[i]["password"]
            f.write("\t{\n")
            f.write(f'\t\t"username": "{username}",\n')
            f.write(f'\t\t"password": "{password}"\n')
            f.write("\t}")
            if i < len(user_database)-1:
                f.write(",")
            f.write("\n")
        f.write("]")


def register_protocol(client_socket: socket.socket, data: str) -> None:
    global existing_username
    data = data.split(":")
    if len(data) != 3:
        client_socket.sendall("REGISTER:ACKSTATUS:2".encode())
        return
    _, username, password = data
    if username not in existing_username:
        create_user_record(username, password)
        client_socket.sendall("REGISTER:ACKSTATUS:0".encode())
    else:
        client_socket.sendall("REGISTER:ACKSTATUS:1".encode())


def process_message(client_socket: socket.socket) -> bool:
    try:
        data = client_socket.recv(8192)
        if not data:
            return False
    except Exception as e:
        print(f"error receiving data: {e}")
        return False
    data = data.decode()
    global clients
    print(f"received from {clients[client_socket]}: {data}")
    if data.split(":")[0] == "LOGIN":
        login_protocol(client_socket, data)
    elif data.split(":")[0] == "REGISTER":
        register_protocol(client_socket, data)
    return True


auth_clients = set()
sockets_list = []
clients = {}


def main(args: list[str]) -> None:
    config(args)
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = ("localhost", server_port)
    server_socket.bind(server_address)
    server_socket.setblocking(False)
    global sockets_list, clients
    sockets_list.append(server_socket)
    server_socket.listen(5)
    print(f"server is listening at {server_address}")

    while True:
        read_sockets, _, exception_sockets = select.select(sockets_list, [], sockets_list)

        for notified_socket in read_sockets:
            if notified_socket == server_socket:
                # new connection
                create_client_socket(server_socket)
            else:
                # a client
                if not process_message(notified_socket):
                    remove_client_socket(notified_socket)

        for notified_socket in exception_sockets:
            remove_client_socket(notified_socket)


if __name__ == "__main__":
    main(sys.argv[1:])
