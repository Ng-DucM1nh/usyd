import sys
import socket
import threading
import tictactoe


client_socket: socket.socket = None
server_address: tuple = ()
most_recent_message: str = ""
user_username: str = ""


def launch_check(args: list[str]) -> None:
    '''
    launch the client program and perform necessary checks
    '''
    if len(args) != 2:
        sys.stderr.write("Error: Expecting 2 arguments: <server address> <port>\n")
        sys.exit(1)
    global client_socket, server_address
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server_address = (args[0], int(args[1]))
        print(f"connecting to server {server_address}")
        client_socket.connect(server_address)
    except:
        sys.stderr.write("Error: cannot connect to server at <server address> and <port>.\n")
        sys.exit(1)


in_room: bool = False


def prompt_message() -> None:
    '''
    prompt for user's message, rewrite it according to the protocol and send to server
    '''
    global most_recent_message
    with client_socket:
        while True:
            try:
                message = input()
            except EOFError:
                sys.exit(1)
            except Exception as e:
                print(f"error prompting for message: {e}")
                sys.exit(1)
            if message == "QUIT":
                sys.exit(0)
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
            elif in_room:
                if not game_begun:
                    continue
                if message == "PLACE":
                    message = prompt_place_protocol()
                elif message == "FORFEIT":
                    message = prompt_forfeit_protocol()
                else:
                    print(f"Unknown command: {message}")
            most_recent_message = message
            client_socket.sendall(f"{message}\n".encode())


def receive_data() -> None:
    '''
    process received messages from server according to protocols
    '''
    while True:
        try:
            data_list = client_socket.recv(8192)
            if not data_list:
                print("no data received")
                sys.exit(0)
        except Exception as e:
            print(f"error receiving data: {e}")
            sys.exit(1)
        data_list = data_list.decode()
        print(f"received from {server_address}: {data_list}")
        for data in data_list.split("\n"):
            if data.split(":")[0] == "LOGIN":
                receive_login_protocol(data)
            elif data.split(":")[0] == "REGISTER":
                receive_register_protocol(data)
            elif data == "BADAUTH":
                sys.stderr.write("Error: You must be logged in to perform this action\n")
            elif data.split(":")[0] == "ROOMLIST":
                receive_roomlist_protocol(data)
            elif data.split(":")[0] == "CREATE":
                receive_create_protocol(data)
            elif data.split(":")[0] == "JOIN":
                receive_join_protocol(data)
            elif data == "NOROOM":
                sys.stderr.write("You are currently not in a room\n")
            elif data.split(":")[0] == "BEGIN":
                receive_begin_protocol(data)
            elif data.split(":")[0] == "BOARDSTATUS":
                receive_boardstatus_protocol(data)
            elif data.split(":")[0] == "INPROGRESS":
                receive_inprogress_protocol(data)
            elif data.split(":")[0] == "GAMEEND":
                receive_gameend_protocol(data)


def prompt_login_protocol() -> str:
    '''
    prompt for user's input and rewrite it to message for LOGIN protocol
    '''
    try:
        username = input("Enter username: ")
    except EOFError:
        sys.exit(0)
    try:
        password = input("Enter password: ")
    except EOFError:
        sys.exit(0)
    return f"LOGIN:{username}:{password}"


def receive_login_protocol(data: str) -> None:
    '''
    process received messages of LOGIN protocol
    '''
    global user_username
    status = data.split(":")[2]
    if status == "3":
        print("wrong format LOGIN message")
        return
    username = most_recent_message.split(":")[1]
    if status == "0":
        print(f"Welcome {username}")
        user_username = username
    elif status == "1":
        sys.stderr.write(f"Error: User {username} not found\n")
    elif status == "2":
        sys.stderr.write(f"Error: Wrong password for user {username}\n")


def prompt_register_protocol() -> str:
    '''
    prompt for user's input and rewrite it to message for REGISTER protocol
    '''
    try:
        username = input("Enter username: ")
    except EOFError:
        sys.exit(0)
    try:
        password = input("Enter password: ")
    except EOFError:
        sys.exit(0)
    return f"REGISTER:{username}:{password}"


def receive_register_protocol(data: str) -> None:
    '''
    process received messages of REGISTER protocol
    '''
    status = data.split(":")[2]
    if status == "2":
        print("wrong format REGISTER message")
        return
    username = most_recent_message.split(":")[1]
    if status == "0":
        print(f"Successfully created user account {username}")
    elif status == "1":
        sys.stderr.write(f"Error: User {username} already exists\n")


def prompt_roomlist_protocol() -> str:
    '''
    prompt for user's input and rewrite it to message for ROOMLIST protocol
    '''
    while True:
        try:
            mode = input("Do you want to have a room list as player or viewer? (Player/Viewer) ")
        except EOFError:
            sys.exit(0)
        mode = mode.upper()
        if mode in ("PLAYER", "VIEWER"):
            break
        print("Unknown input.")
    return f"ROOMLIST:{mode}"


def receive_roomlist_protocol(data: str) -> None:
    '''
    process received messages of ROOMLIST protocol
    '''
    data = data.split(":")
    status = data[2]
    if status == "1":
        sys.stderr.write("Error: Please input a valid mode.\n")
        return
    mode = most_recent_message.split(":")[1]
    room_list = data[3]
    print(f"Room available to join as {mode}: {room_list}")


def prompt_create_protocol() -> str:
    '''
    prompt for user's input and rewrite it to message for CREATE protocol
    '''
    try:
        room_name = input("Enter room name you want to create: ")
    except EOFError:
        sys.exit(0)
    return f"CREATE:{room_name}"


def receive_create_protocol(data: str) -> None:
    '''
    process received messages of CREATE protocol
    '''
    global in_room, is_player
    status = data.split(":")[2]
    if status == "4":
        print("wrong format CREATE message")
        return
    room_name = most_recent_message.split(":")[1]
    if status == "0":
        print(f"Successfully created room {room_name}")
        in_room = True
        is_player = True
        print("Waiting for other player...")
    elif status == "1":
        sys.stderr.write(f"Error: Room {room_name} is invalid\n")
    elif status == "2":
        sys.stderr.write(f"Error: Room {room_name} already exists\n")
    elif status == "3":
        sys.stderr.write(f"Error: Server already contains a maximum of {ROOMS_LIMIT} rooms\n")


def prompt_join_protocol() -> str:
    '''
    prompt for user's input and rewrite it to message for JOIN protocol
    '''
    try:
        room_name = input("Enter room name you want to join: ")
    except EOFError:
        sys.exit(0)
    while True:
        try:
            mode = input("You wish to join the room as: (Player/Viewer) ")
        except EOFError:
            sys.exit(0)
        mode = mode.upper()
        if mode not in ("PLAYER", "VIEWER"):
            print("Unknown input.")
        else:
            break
    return f"JOIN:{room_name}:{mode}"


is_player: bool = False


def receive_join_protocol(data: str) -> None:
    '''
    process received messages of JOIN protocol
    '''
    global in_room, is_player
    status = data.split(":")[2]
    if status == "3":
        print("wrong format JOIN message")
        return
    _, room_name, mode = most_recent_message.split(":")
    if status == "1":
        sys.stderr.write(f"Error: No room named {room_name}\n")
    elif status == "2":
        sys.stderr.write(f"Error: The room {room_name} already has 2 players\n")
    elif status == "0":
        print(f"Successfully joined room {room_name} as a {mode}")
        in_room = True
        is_player = mode == "PLAYER"
        print("Waiting for other player...")


is_p1_turn: bool = False
game_begun: bool = False

board: list[list[str]]

p1_username: str = ""
p2_username: str = ""

def receive_begin_protocol(data: str) -> None:
    '''
    process received messages of BEGIN protocol
    '''
    global is_p1_turn, game_begun, board, p1_username, p2_username
    _, p1, p2 = data.split(":")
    p1_username = p1
    p2_username = p2
    print(f"match between {p1} and {p2} will commence, it is currently {p1}’s turn.")
    if user_username in (p1, p2):
        game_begun = True
        is_p1_turn = True
    board = tictactoe.create_board()


def receive_boardstatus_protocol(data: str) -> None:
    '''
    process received messages of BOARDSTATUS protocol
    '''
    global is_p1_turn, board
    status = data.split(":")[1]
    board = tictactoe.assign_board(status)
    tictactoe.print_board(board)
    is_p1_turn = not is_p1_turn
    if is_player:
        if is_p1_turn:
            if user_username == p1_username:
                print("It is the current player's turn")
            else:
                print("It is the opposing player's turn")
        else:
            if user_username == p1_username:
                print("It is the opposing player's turn")
            else:
                print("It is the current player's turn")
    else:
        if is_p1_turn:
            print(f"It is {p1_username}'s turn")
        else:
            print(f"It is {p2_username}'s turn")


def prompt_place_protocol() -> str:
    '''
    prompt for user's input and rewrite it to message for PLACE protocol
    '''
    while True:
        try:
            col = int(input("Column: "))
            row = int(input("Row: "))
        except EOFError:
            sys.exit(0)
        except:
            print("(Column/Row) values must be an integer between 0 and 2")
            continue
        if row < 0 or row > 2 or col < 0 or col > 2:
            print("(Column/Row) values must be an integer between 0 and 2")
            continue
        if tictactoe.get_marker(board, row, col) != ' ':
            print(f"({col}, {row}) is occupied by {tictactoe.get_marker(board, row, col)}.")
            continue
        break
    return f"PLACE:{col}:{row}"


def receive_gameend_protocol(data: str) -> None:
    '''
    process received messages of GAMEEND protocol
    '''
    global board, game_begun, in_room, is_p1_turn, p1_username, p2_username, is_player
    board_status, status_code = data.split(":")[1:3]
    board = tictactoe.assign_board(board_status)
    tictactoe.print_board(board)
    if status_code == "1":
        print("Game ended in a draw")
    elif status_code == "0":
        winner_username = data.split(":")[3]
        if is_player:
            if user_username == winner_username:
                print("Congratulations, you won!")
            else:
                print("Sorry you lost. Good luck next time.")
        else:
            print(f"{winner_username} has won this game")
    elif status_code == "2":
        winner_username = data.split(":")[3]
        print(f"{winner_username} won due to the opposing player forfeiting")
    board = None
    game_begun = False
    in_room = False
    is_player = False
    is_p1_turn = False
    p1_username = ""
    p2_username = ""


def prompt_forfeit_protocol() -> str:
    '''
    prompt for user's input and rewrite it to message for FORFEIT protocol
    '''
    return "FORFEIT"


def receive_inprogress_protocol(data: str) -> None:
    '''
    process received messages of INPROGRESS protocol
    '''
    global p1_username, p2_username, is_p1_turn
    _, current_turn_player, opposing_player = data.split(":")
    p1_username = current_turn_player
    p2_username = opposing_player
    is_p1_turn = True
    print(f"Match between {current_turn_player} and {opposing_player} is currently in progress, it is {current_turn_player}’s turn")


ROOMS_LIMIT: int = 2


def main(args: list[str]) -> None:
    launch_check(args)
    receive_thread = threading.Thread(target=receive_data)
    receive_thread.daemon = True
    receive_thread.start()
    prompt_message()


if __name__ == "__main__":
    main(sys.argv[1:])
