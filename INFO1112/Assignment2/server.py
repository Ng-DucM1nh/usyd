import sys
import socket
import select
import os
import json
import bcrypt
import tictactoe


class Room:

    def __init__(self, room_name: str):
        self.room_name = room_name
        self.p1_username = ""
        self.p2_username = ""
        self.p1_client_socket = None
        self.p2_client_socket = None
        self.viewers_client_socket = []
        self.current_turn_player = ""
        self.board = None

    def has_player1(self) -> bool:
        return self.p1_client_socket is not None

    def has_player2(self) -> bool:
        return self.p2_client_socket is not None

    def get_player1(self) -> tuple[str, socket.socket] | None:
        return self.p1_username, self.p1_client_socket if self.has_player1() else None

    def get_player2(self) -> tuple[str, socket.socket] | None:
        return self.p2_username, self.p2_client_socket if self.has_player2() else None

    def get_viewers(self) -> list[socket.socket]:
        return self.viewers_client_socket

    def add_player(self, username: str, client_socket: socket.socket) -> bool:
        if not self.has_player1():
            self.p1_username = username
            self.p1_client_socket = client_socket
            return False
        self.p2_username = username
        self.p2_client_socket = client_socket
        self.current_turn_player = self.p1_username
        return True

    def add_viewer(self, client_socket: socket.socket) -> None:
        self.viewers_client_socket.append(client_socket)

    def send_message(self, message: str) -> None:
        p1_client_socket = self.p1_client_socket
        p2_client_socket = self.p2_client_socket
        p1_client_socket.sendall(message.encode())
        p2_client_socket.sendall(message.encode())
        for viewer_client_socket in self.viewers_client_socket:
            viewer_client_socket.sendall(message.encode())

    def destroy(self) -> None:
        global client_room, full_rooms
        p1_client_socket = self.p1_client_socket
        p2_client_socket = self.p2_client_socket
        client_room.pop(p1_client_socket)
        client_room.pop(p2_client_socket)
        for viewer_client_socket in self.viewers_client_socket:
            client_room.pop(viewer_client_socket)
        full_rooms.pop(self.room_name)

    def swap_turn(self) -> None:
        self.current_turn_player = self.p2_username if self.current_turn_player == self.p1_username else self.p1_username


pending_rooms: dict[str, Room] = {}
full_rooms: dict[str, Room] = {}


server_port: int = 0
user_database_path: str = ""
user_database: list[dict] = []
existing_username: set = set()


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
    try:
        server_port = int(server_port)
    except:
        sys.stderr.write(f"Error: port number out of range")
        exit(1)
    if server_port < 1024 or server_port > 65535:
        sys.stderr.write(f"Error: port number out of range")
        exit(1)
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
    global sockets_list, clients, auth_clients, client_room
    print(f"disconnection from {clients[client_socket]}")
    if client_socket in client_room:
        room_name = client_room[client_socket]
        # if room_name in pending_rooms:
        #     p1_username = room.get_player1()[0]
        #     gameend_protocol
        if room_name in full_rooms:
            room = full_rooms[room_name]
            p1_username = room.get_player1()[0]
            p2_username = room.get_player2()[0]
            client_username = auth_clients[client_socket]
            if client_username == p1_username:
                gameend_protocol(room, "2", p2_username)
            elif client_username == p2_username:
                gameend_protocol(room, "2", p1_username)
    sockets_list.remove(client_socket)
    del clients[client_socket]
    auth_clients.pop(client_socket, None)
    client_room.pop(client_socket, None)


def login_protocol(client_socket: socket.socket, data: str) -> None:
    global auth_clients
    data = data.split(":")
    if len(data) != 3:
        client_socket.sendall("LOGIN:ACKSTATUS:3\n".encode())
        return
    _, username, password = data
    for user in user_database:
        if user["username"] != username:
            continue
        if bcrypt.checkpw(password.encode(), user["password"].encode()):
            client_socket.sendall("LOGIN:ACKSTATUS:0\n".encode())
            auth_clients[client_socket] = username
            return
        else:
            client_socket.sendall("LOGIN:ACKSTATUS:2\n".encode())
            return
    # username not found in user database
    client_socket.sendall("LOGIN:ACKSTATUS:1\n".encode())


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
        client_socket.sendall("REGISTER:ACKSTATUS:2\n".encode())
        return
    _, username, password = data
    if username not in existing_username:
        create_user_record(username, password)
        client_socket.sendall("REGISTER:ACKSTATUS:0\n".encode())
    else:
        client_socket.sendall("REGISTER:ACKSTATUS:1\n".encode())


def roomlist_protocol(client_socket: socket.socket, data: str) -> None:
    global pending_rooms, full_rooms
    data = data.split(":")
    if len(data) != 2:
        client_socket.sendall("ROOMLIST:ACKSTATUS:1\n".encode())
        return
    mode = data[1]
    if mode != "PLAYER" and mode != "VIEWER":
        client_socket.sendall("ROOMLIST:ACKSTATUS:1\n".encode())
        return
    room_list = ""
    if mode == "PLAYER":
        room_list = ",".join(pending_rooms)
    elif mode == "VIEWER":
        room_list = ",".join(list(pending_rooms.keys()) + list(full_rooms.keys()))
    client_socket.sendall(f"ROOMLIST:ACKSTATUS:0:{room_list}\n".encode())


def valid_room_name(room_name: str) -> bool:
    if len(room_name) >= 20:
        return False
    for c in room_name:
        if not (c.isalnum() or c == "-" or c == " " or c == "_"):
            return False
    return True


def add_client_to_room(client_socket: socket.socket, mode: str, room_name: str) -> None:
    global client_room, pending_rooms, full_rooms
    client_room[client_socket] = room_name
    if mode == "PLAYER":
        if pending_rooms[room_name].add_player(auth_clients[client_socket], client_socket):
            full_rooms[room_name] = pending_rooms[room_name]
            pending_rooms.pop(room_name)
            begin_protocol(full_rooms[room_name])
    elif mode == "VIEWER":
        if room_name in pending_rooms:
            pending_rooms[room_name].add_viewer(client_socket)
        elif room_name in full_rooms:
            full_rooms[room_name].add_viewer(client_socket)
            inprogress_protocol(client_socket)

def create_protocol(client_socket: socket.socket, data: str) -> None:
    data = data.split(":")
    if len(data) != 2:
        client_socket.sendall("CREATE:ACKSTATUS:4\n".encode())
        return
    room_name = data[1]
    if len(pending_rooms) + len(full_rooms) == ROOMS_LIMIT:
        client_socket.sendall("CREATE:ACKSTATUS:3\n".encode())
        return
    if not valid_room_name(room_name):
        client_socket.sendall("CREATE:ACKSTATUS:1\n".encode())
        return
    if room_name in pending_rooms or room_name in full_rooms:
        client_socket.sendall("CREATE:ACKSTATUS:2\n".encode())
        return
    pending_rooms[room_name] = Room(room_name)
    add_client_to_room(client_socket, "PLAYER", room_name)
    client_socket.sendall("CREATE:ACKSTATUS:0\n".encode())


def join_protocol(client_socket: socket.socket, data: str) -> None:
    data = data.split(":")
    if len(data) != 3:
        client_socket.sendall("JOIN:ACKSTATUS:3\n".encode())
        return
    _, room_name, mode = data
    if mode != "PLAYER" and mode != "VIEWER":
        client_socket.sendall("JOIN:ACKSTATUS:3\n".encode())
        return
    if room_name not in pending_rooms and room_name not in full_rooms:
        client_socket.sendall("JOIN:ACKSTATUS:1\n".encode())
        return
    if mode == "PLAYER" and room_name not in pending_rooms:
        client_socket.sendall("JOIN:ACKSTATUS:2\n".encode())
        return
    client_socket.sendall("JOIN:ACKSTATUS:0\n".encode())
    add_client_to_room(client_socket, mode, room_name)


def begin_protocol(room: Room) -> None:
    p1_username = room.get_player1()[0]
    p2_username = room.get_player2()[0]
    room.board = tictactoe.create_board()
    room.send_message(f"BEGIN:{p1_username}:{p2_username}\n")


def place_protocol(client_socket: socket.socket, data: str) -> None:
    global full_rooms, client_room, auth_clients
    room = full_rooms[client_room[client_socket]]
    username = auth_clients[client_socket]
    p1 = room.get_player1()[0]
    marker = 'X' if username == p1 else 'O'
    _, col, row = data.split(":")
    col = int(col)
    row = int(row)
    room.board = tictactoe.put_marker(room.board, row, col, marker)
    if tictactoe.player_wins(marker, room.board):
        gameend_protocol(room, "0", username)
        return
    if tictactoe.players_draw(room.board):
        gameend_protocol(room, "1")
        return
    boardstatus_protocol(room)


def gameend_protocol(room: Room, status_code: str, *winner_username) -> None:
    board_status = tictactoe.get_board_status(room.board)
    if winner_username:
        message = f"GAMEEND:{board_status}:{status_code}:{winner_username[0]}\n"
    else:
        message = f"GAMEEND:{board_status}:{status_code}\n"
    room.send_message(message)
    room.destroy()


def boardstatus_protocol(room: Room) -> None:
    board_status = tictactoe.get_board_status(room.board)
    room.swap_turn()
    print(f"sending BOARDSTATUS message, the next turn player is {room.current_turn_player}")
    message = f"BOARDSTATUS:{board_status}\n"
    room.send_message(message)


def forfeit_protocol(client_socket: socket.socket, data: str) -> None:
    global full_rooms, auth_clients, client_room
    room = full_rooms[client_room[client_socket]]
    username = auth_clients[client_socket]
    p1_username = room.get_player1()[0]
    p2_username = room.get_player2()[0]
    opponent = p2_username if username == p1_username else p1_username
    gameend_protocol(room, "2", opponent)


def inprogress_protocol(client_socket: socket.socket) -> None:
    global full_rooms, client_room
    room = full_rooms[client_room[client_socket]]
    p1_username = room.get_player1()[0]
    p2_username = room.get_player2()[0]
    current_turn_player = room.current_turn_player
    opposing_player = p1_username if current_turn_player == p2_username else p2_username
    client_socket.sendall(f"INPROGRESS:{current_turn_player}:{opposing_player}\n".encode())


def process_message(client_socket: socket.socket) -> bool:
    try:
        data_list = client_socket.recv(8192)
        if not data_list:
            return False
    except Exception as e:
        print(f"error receiving data: {e}")
        return False
    data_list = data_list.decode()
    global clients
    print(f"received from {clients[client_socket]}: {data_list}")
    for data in data_list.split("\n"):
        if data.split(":")[0] == "LOGIN":
            login_protocol(client_socket, data)
            return True
        if data.split(":")[0] == "REGISTER":
            register_protocol(client_socket, data)
            return True
        if client_socket not in auth_clients:
            client_socket.sendall("BADAUTH\n".encode())
            return True
        if data.split(":")[0] == "ROOMLIST":
            roomlist_protocol(client_socket, data)
            return True
        if data.split(":")[0] == "CREATE":
            create_protocol(client_socket, data)
            return True
        if data.split(":")[0] == "JOIN":
            join_protocol(client_socket, data)
            return True
        if client_socket not in client_room:
            client_socket.sendall("NOROOM\n".encode())
            return True
        if data.split(":")[0] == "PLACE":
            place_protocol(client_socket, data)
            return True
        if data.split(":")[0] == "FORFEIT":
            forfeit_protocol(client_socket, data)
            return True
    return True


auth_clients: dict[socket.socket, str] = {}
sockets_list: list[socket.socket] = []
clients: dict[socket.socket, str] = {}
client_room: dict[socket.socket, str] = {}

ROOMS_LIMIT: int = 2

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
