import sys
import socket
import threading
import tictactoe


client_socket: socket.socket = None
server_address: tuple = ()
most_recent_message: str = ""
user_username: str = ""


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


in_room: bool = False


def prompt_message() -> None:
    global client_socket, most_recent_message, game_begun, is_user_turn, in_room
    with client_socket:
        while True:
            try:
                message = input()
            except EOFError:
                exit(1)
            except Exception as e:
                print(f"error prompting for message: {e}")
                exit(1)
            if message == "QUIT":
                exit(0)
            if not in_room:
                if message == "LOGIN":
                    message = prompt_login_protocol()
                elif message == "REGISTER":
                    message = prompt_register_protocol()
                elif message == "ROOMLIST":
                    message = prompt_roomlist_protocol()
                elif message == "CREATE":
                    message = prompt_create_protocol()
                elif message == "JOIN":
                    message = prompt_join_protocol()
                else:
                    print(f"Unknown command: {message}")
            else:
                if not game_begun:
                    print("waiting for opponent")
                    continue
                if not is_user_turn:
                    print("waiting for opponent to place marker")
                    continue
                if message == "PLACE":
                    message = prompt_place_protocol()
                else:
                    print(f"Unknown command: {message}")
            most_recent_message = message
            client_socket.sendall(f"{message}\n".encode())


def receive_data() -> None:
    global client_socket, server_address
    while True:
        try:
            data_list = client_socket.recv(8192)
            if not data_list:
                print(f"no data received")
                exit(0)
        except Exception as e:
            print(f"error receiving data: {e}")
            exit(1)
        data_list = data_list.decode()
        print(f"received from {server_address}: {data_list}")
        for data in data_list.split("\n"):
            if data.split(":")[0] == "LOGIN":
                receive_login_protocol(data)
            elif data.split(":")[0] == "REGISTER":
                receive_register_protocol(data)
            elif data == "BADAUTH":
                print("Error: You must be logged in to perform this action")
            elif data.split(":")[0] == "ROOMLIST":
                receive_roomlist_protocol(data)
            elif data.split(":")[0] == "CREATE":
                receive_create_protocol(data)
            elif data.split(":")[0] == "JOIN":
                receive_join_protocol(data)
            elif data.split(":")[0] == "BEGIN":
                receive_begin_protocol(data)
            elif data.split(":")[0] == "BOARDSTATUS":
                receive_boardstatus_protocol(data)


def prompt_login_protocol() -> str:
    try:
        username = input("Enter username: ")
    except EOFError:
        exit(0)
    try:
        password = input("Enter password: ")
    except EOFError:
        exit(0)
    return f"LOGIN:{username}:{password}"


def receive_login_protocol(data: str) -> None:
    # response of a recent LOGIN message
    global most_recent_message, user_username
    status = data.split(":")[2]
    if status == "3":
        print(f"wrong format LOGIN message")
        return
    username = most_recent_message.split(":")[1]
    if status == "0":
        print(f"Welcome {username}")
        user_username = username
    elif status == "1":
        print(f"Error: User {username} not found")
    elif status == "2":
        print(f"Error: Wrong password for user {username}")


def prompt_register_protocol() -> str:
    try:
        username = input("Enter username: ")
    except EOFError:
        exit(0)
    try:
        password = input("Enter password: ")
    except EOFError:
        exit(0)
    return f"REGISTER:{username}:{password}"


def receive_register_protocol(data: str) -> None:
    global most_recent_message
    status = data.split(":")[2]
    if status == "2":
        print(f"wrong format REGISTER message")
        return
    username = most_recent_message.split(":")[1]
    if status == "0":
        print(f"Successfully created user account {username}")
    elif status == "1":
        print(f"Error: User {username} already exists")


def prompt_roomlist_protocol() -> str:
    while True:
        try:
            mode = input("Do you want to have a room list as player or viewer? (Player/Viewer) ")
        except EOFError:
            exit(0)
        mode = mode.upper()
        if mode == "PLAYER" or mode == "VIEWER":
            break
        else:
            print("Unknown input.")
    return f"ROOMLIST:{mode}"


def receive_roomlist_protocol(data: str) -> None:
    global most_recent_message
    data = data.split(":")
    status = data[2]
    if status == "1":
        print(f"ClientError: Please input a valid mode.")
        return
    mode = most_recent_message.split(":")[1]
    room_list = data[3]
    print(f"Room available to join as {mode}: {room_list}")


def prompt_create_protocol() -> str:
    try:
        room_name = input("Enter room name you want to create: ")
    except EOFError:
        exit(0)
    return f"CREATE:{room_name}"


def receive_create_protocol(data: str) -> None:
    global most_recent_message
    status = data.split(":")[2]
    if status == "4":
        print(f"wrong format CREATE message")
        return
    room_name = most_recent_message.split(":")[1]
    if status == "0":
        print(f"Successfully created room {room_name}")
    elif status == "1":
        print(f"Error: Room {room_name} is invalid")
    elif status == "2":
        print(f"Error: Room {room_name} already exists")
    elif status == "3":
        print(f"Error: Server already contains a maximum of {ROOMS_LIMIT} rooms")


def prompt_join_protocol() -> str:
    try:
        room_name = input("Enter room name you want to join: ")
    except EOFError:
        exit(0)
    while True:
        try:
            mode = input("You wish to join the room as: (Player/Viewer) ")
        except EOFError:
            exit(0)
        mode = mode.upper()
        if mode != "PLAYER" and mode != "VIEWER":
            print("Unknown input.")
        else:
            break
    return f"JOIN:{room_name}:{mode}"


def receive_join_protocol(data: str) -> None:
    global most_recent_message, in_room
    status = data.split(":")[2]
    if status == "3":
        print(f"wrong format JOIN message")
        return
    _, room_name, mode = most_recent_message.split(":")
    if status == "1":
        print(f"Error: No room named {room_name}")
    elif status == "2":
        print(f"Error: The room {room_name} already has 2 players")
    elif status == "0":
        print(f"Successfully joined room {room_name} as a {mode}")
        in_room = True


is_user_turn: bool = False
game_begun: bool = False

board = None

def receive_begin_protocol(data: str) -> None:
    global is_user_turn, game_begun, user_username, board
    _, p1, p2 = data.split(":")
    print(f"match between {p1} and {p2} will commence, it is currently {p1}’s turn.")
    game_begun = True
    is_user_turn = (p1 == user_username)
    print(f"la sao zayyyyy {is_user_turn}")
    board = tictactoe.create_board()


def receive_boardstatus_protocol(data: str) -> None:
    global is_user_turn, board
    status = data.split(":")[1]
    board = tictactoe.assign_board(status)
    tictactoe.print_board(board)
    print(f"truoc kia {is_user_turn}")
    is_user_turn = not is_user_turn
    print(f"wueeee {is_user_turn}")
    if is_user_turn:
        print(f"It is the current player’s turn")
    else:
        print(f"It is the opposing player’s turn")


def prompt_place_protocol() -> str:
    global board
    while True:
        try:
            col = int(input("Column: "))
            row = int(input("Row: "))
        except EOFError:
            exit(0)
        except:
            print(f"(Column/Row) values must be an integer between 0 and 2")
            continue
        if row < 0 or row > 2 or col < 0 or col > 2:
            print(f"(Column/Row) values must be an integer between 0 and 2")
            continue
        if tictactoe.get_marker(board, row, col) != ' ':
            print(f"({col}, {row}) is occupied by {tictactoe.get_marker(board, row, col)}.")
            continue
        break
    return f"PLACE:{col}:{row}"


ROOMS_LIMIT: int = 2


def main(args: list[str]) -> None:
    launch_check(args)
    receive_thread = threading.Thread(target=receive_data)
    receive_thread.daemon = True
    receive_thread.start()
    prompt_message()


if __name__ == "__main__":
    main(sys.argv[1:])
