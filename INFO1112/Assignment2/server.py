import sys
import socket
import select
import os
import json
import bcrypt
import tictactoe


class Room:
    '''
    A class to simulate a Tic Tac Toe game room

    Attributes:
    -----------
    room_name: str
        the room's name
    p1_username: str
        username of player 1
    p2_username: str
        username of player 2
    p1_client_socket: socket.socket or None
        the client socket of player 1, used for communication
    p2_client_socket: socket.socket or None
        the client socket of player 2, used for communication
    viewers_client_socket: list[socket.socket]
        a list containing the client sockets of viewers in the room
    current_turn_player: str
        username of the player who is currently in turn
    board: list[list[str]] or None
        the current tic tac toe board as a 2D list of strings
    '''
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
        '''
        check if player 1 is present
        '''
        return self.p1_client_socket is not None

    def has_player2(self) -> bool:
        '''
        check if player 2 is present
        '''
        return self.p2_client_socket is not None

    def get_player1(self) -> tuple[str, socket.socket] | None:
        '''
        return player 1's username and client socket if present, else None
        '''
        return self.p1_username, self.p1_client_socket if self.has_player1() else None

    def get_player2(self) -> tuple[str, socket.socket] | None:
        '''
        return player 2's username and client socket if present, else None
        '''
        return self.p2_username, self.p2_client_socket if self.has_player2() else None

    def get_viewers(self) -> list[socket.socket]:
        '''
        return a list of viewer client sockets
        '''
        return self.viewers_client_socket

    def add_player(self, username: str, client_socket: socket.socket) -> bool:
        '''
        add a player to the room
        return True if it's the second player, else return False
        '''
        if not self.has_player1():
            self.p1_username = username
            self.p1_client_socket = client_socket
            return False
        self.p2_username = username
        self.p2_client_socket = client_socket
        self.current_turn_player = self.p1_username
        return True

    def add_viewer(self, client_socket: socket.socket) -> None:
        '''
        add a viewer to the room
        '''
        self.viewers_client_socket.append(client_socket)

    def send_message(self, message: str) -> None:
        '''
        send a message to all clients in the room, including both players and viewers
        '''
        p1_client_socket = self.p1_client_socket
        p2_client_socket = self.p2_client_socket
        p1_client_socket.sendall(message.encode())
        p2_client_socket.sendall(message.encode())
        for viewer_client_socket in self.viewers_client_socket:
            viewer_client_socket.sendall(message.encode())

    def swap_turn(self) -> None:
        '''
        swap the current turn between 2 players
        '''
        if self.current_turn_player == self.p1_username:
            self.current_turn_player = self.p2_username
        else:
            self.current_turn_player = self.p1_username

    def destroy(self) -> None:
        '''
        removes the room and its players/viewers from the global tracking databases
        '''
        p1_client_socket = self.p1_client_socket
        p2_client_socket = self.p2_client_socket
        client_room.pop(p1_client_socket)
        client_room.pop(p2_client_socket)
        for viewer_client_socket in self.viewers_client_socket:
            client_room.pop(viewer_client_socket)
        full_rooms.pop(self.room_name)

pending_rooms: dict[str, Room] = {}
full_rooms: dict[str, Room] = {}


server_port: int = 0
user_database_path: str = ""
user_database: list[dict] = []
existing_username: set = set()


def config(args: list[str]) -> None:
    '''
    launch the server and perform necessary checks
    '''
    if len(args) != 1:
        sys.stderr.write("Error: Expecting 1 argument: <server config path>.\n")
        sys.exit(1)
    server_config_path = args[0]
    server_config_path = os.path.expanduser(server_config_path)
    server_config_path = os.path.abspath(server_config_path)
    if not os.path.exists(server_config_path):
        sys.stderr.write("Error: <server config path> doesn't exist.\n")
        sys.exit(1)
    try:
        with open(server_config_path) as fileobj:
            data = json.load(fileobj)
    except json.decoder.JSONDecodeError:
        sys.stderr.write("Error: <server config path> is not in a valid JSON format.\n")
        sys.exit(1)
    missing_key = []
    if "port" not in data.keys():
        missing_key.append("port")
    if "userDatabase" not in data.keys():
        missing_key.append("userDatabase")
    if len(missing_key) > 0:
        sys.stderr.write("Error: <server config path> missing key(s): ")
        for i, key in enumerate(missing_key):
            sys.stderr.write(missing_key[i])
            sys.stderr.write(key)
            if i < len(missing_key)-1:
                sys.stderr.write(", ")
        sys.stderr.write("\n")
        sys.exit(1)

    global server_port, user_database_path
    server_port = data["port"]
    try:
        server_port = int(server_port)
    except:
        sys.stderr.write("Error: port number out of range")
        sys.exit(1)
    if server_port < 1024 or server_port > 65535:
        sys.stderr.write("Error: port number out of range")
        sys.exit(1)
    user_database_path = data["userDatabase"]
    user_database_path = os.path.expanduser(user_database_path)
    user_database_path = os.path.abspath(user_database_path)
    if not os.path.exists(user_database_path):
        sys.stderr.write("Error: <user database path> doesn't exist.\n")
        sys.exit(1)
    try:
        with open(user_database_path) as fileobj:
            data = json.load(fileobj)
    except json.decoder.JSONDecodeError:
        sys.stderr.write("Error: <user database path> is not in a valid JSON format.\n")
        sys.exit(1)
    if not isinstance(data, list):
        sys.stderr.write("Error: <user database path> is not a JSON array.\n")
        sys.exit(1)
    for account in data:
        keys = sorted(account.keys())
        if keys != ["password", "username"]:
            sys.stderr.write("Error: <user database path> contains invalid user record formats.\n")
            sys.exit(1)

    global user_database
    user_database = data
    for user in user_database:
        existing_username.add(user["username"])


def create_client_socket(server_socket: socket.socket) -> None:
    '''
    create a new client socket and add it to global tracking databases
    '''
    client_socket, client_address = server_socket.accept()
    client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    client_socket.setblocking(False)
    sockets_list.append(client_socket)
    clients[client_socket] = client_address
    print(f"new connection from {client_address}")


def remove_client_socket(client_socket: socket.socket) -> None:
    '''
    remove a client socket from global tracking databases
    '''
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
    '''
    handle the LOGIN protocol
    '''
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
        client_socket.sendall("LOGIN:ACKSTATUS:2\n".encode())
        return
    # username not found in user database
    client_socket.sendall("LOGIN:ACKSTATUS:1\n".encode())


def create_user_record(username: str, password: str) -> None:
    '''
    create a new user recode and add it to the user database file
    '''
    user_record = {"username":username, "password":bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()}
    user_database.append(user_record)
    existing_username.add(username)
    with open(user_database_path, "w") as f:
        f.write("[\n")
        for i, user in enumerate(user_database):
            username = user["username"]
            password = user["password"]
            f.write("\t{\n")
            f.write(f'\t\t"username": "{username}",\n')
            f.write(f'\t\t"password": "{password}"\n')
            f.write("\t}")
            if i < len(user_database)-1:
                f.write(",")
            f.write("\n")
        f.write("]")


def register_protocol(client_socket: socket.socket, data: str) -> None:
    '''
    handle the REGISTER protocol
    '''
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
    '''
    handle the ROOMLIST protocol
    '''
    data = data.split(":")
    if len(data) != 2:
        client_socket.sendall("ROOMLIST:ACKSTATUS:1\n".encode())
        return
    mode = data[1]
    if mode not in("PLAYER", "VIEWER"):
        client_socket.sendall("ROOMLIST:ACKSTATUS:1\n".encode())
        return
    room_list = ""
    if mode == "PLAYER":
        room_list = ",".join(pending_rooms)
    elif mode == "VIEWER":
        room_list = ",".join(list(pending_rooms.keys()) + list(full_rooms.keys()))
    client_socket.sendall(f"ROOMLIST:ACKSTATUS:0:{room_list}\n".encode())


def valid_room_name(room_name: str) -> bool:
    '''
    check if <room_name> is a valid name for a room
    '''
    if len(room_name) >= 20:
        return False
    for c in room_name:
        if not (c.isalnum() or c == "-" or c == " " or c == "_"):
            return False
    return True


def add_client_to_room(client_socket: socket.socket, mode: str, room_name: str) -> None:
    '''
    add a client to a room with the name <room_name>
    the client can be either player or viewer, specified by <mode>
    '''
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
    '''
    handle the CREATE protocol
    '''
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
    '''
    handle the JOIN protocol
    '''
    data = data.split(":")
    if len(data) != 3:
        client_socket.sendall("JOIN:ACKSTATUS:3\n".encode())
        return
    _, room_name, mode = data
    if mode not in ("PLAYER", "VIEWER"):
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
    '''
    handle the BEGIN protocol
    '''
    p1_username = room.get_player1()[0]
    p2_username = room.get_player2()[0]
    room.board = tictactoe.create_board()
    room.send_message(f"BEGIN:{p1_username}:{p2_username}\n")


def place_protocol(client_socket: socket.socket, data: str) -> None:
    '''
    handle the PLACE protocol
    '''
    client_room_name = client_room[client_socket]
    if client_room_name in pending_rooms:
        return
    room = full_rooms[client_room_name]
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
    '''
    handle the GAMEEND protocol
    '''
    board_status = tictactoe.get_board_status(room.board)
    if winner_username:
        message = f"GAMEEND:{board_status}:{status_code}:{winner_username[0]}\n"
    else:
        message = f"GAMEEND:{board_status}:{status_code}\n"
    room.send_message(message)
    room.destroy()


def boardstatus_protocol(room: Room) -> None:
    '''
    handle the BOARDSTATUS protocol
    '''
    board_status = tictactoe.get_board_status(room.board)
    room.swap_turn()
    print(f"sending BOARDSTATUS message, the next turn player is {room.current_turn_player}")
    message = f"BOARDSTATUS:{board_status}\n"
    room.send_message(message)


def forfeit_protocol(client_socket: socket.socket) -> None:
    '''
    handle the FORFEIT protocol
    '''
    room = full_rooms[client_room[client_socket]]
    username = auth_clients[client_socket]
    p1_username = room.get_player1()[0]
    p2_username = room.get_player2()[0]
    opponent = p2_username if username == p1_username else p1_username
    gameend_protocol(room, "2", opponent)


def inprogress_protocol(client_socket: socket.socket) -> None:
    '''
    handle the INPROGRESS protocol
    '''
    room = full_rooms[client_room[client_socket]]
    p1_username = room.get_player1()[0]
    p2_username = room.get_player2()[0]
    current_turn_player = room.current_turn_player
    opposing_player = p1_username if current_turn_player == p2_username else p2_username
    client_socket.sendall(f"INPROGRESS:{current_turn_player}:{opposing_player}\n".encode())


def process_message(client_socket: socket.socket) -> bool:
    '''
    process received message and respond accordingly to protocols
    return False if no data is received or there is an error raises
    return True otherwise
    '''
    try:
        data_list = client_socket.recv(8192)
        if not data_list:
            return False
    except Exception as e:
        print(f"error receiving data: {e}")
        return False
    data_list = data_list.decode()
    print(f"received from {clients[client_socket]}: {data_list}")
    for i, data in enumerate(data_list.split("\n")):
        if i == len(data_list.split("\n")) - 1:
            continue
        if data.split(":")[0] == "LOGIN":
            login_protocol(client_socket, data)
        elif data.split(":")[0] == "REGISTER":
            register_protocol(client_socket, data)
        elif client_socket not in auth_clients:
            client_socket.sendall("BADAUTH\n".encode())
        elif data.split(":")[0] == "ROOMLIST":
            roomlist_protocol(client_socket, data)
        elif data.split(":")[0] == "CREATE":
            create_protocol(client_socket, data)
        elif data.split(":")[0] == "JOIN":
            join_protocol(client_socket, data)
        elif client_socket not in client_room:
            client_socket.sendall("NOROOM\n".encode())
        elif data.split(":")[0] == "PLACE":
            place_protocol(client_socket, data)
        elif data.split(":")[0] == "FORFEIT":
            forfeit_protocol(client_socket)
    return True


auth_clients: dict[socket.socket, str] = {}
sockets_list: list[socket.socket] = []
clients: dict[socket.socket, str] = {}
client_room: dict[socket.socket, str] = {}

ROOMS_LIMIT: int = 256

def main(args: list[str]) -> None:
    config(args)
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    server_address = ("localhost", server_port)
    server_socket.bind(server_address)
    server_socket.setblocking(False)
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
