import sys
import socket
import threading


client_socket: socket.socket = None
server_address: tuple = ()
most_recent_message: str = ""


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


waiting: bool = False


def prompt_message() -> None:
    global client_socket, most_recent_message, waiting
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
            if waiting:
                print("waiting for opponent")
                continue
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
            most_recent_message = message
            client_socket.sendall(f"{message}\n".encode())


def receive_data() -> None:
    global client_socket, server_address, waiting
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
                waiting = False
                print(f"THE GAME BEGINSSSS YEEEEEEEE")


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
    global most_recent_message
    status = data.split(":")[2]
    if status == "3":
        print(f"wrong format LOGIN message")
        return
    username = most_recent_message.split(":")[1]
    if status == "0":
        print(f"Welcome {username}")
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
    global most_recent_message, waiting
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
        print("waiting for opponent")
        waiting = True


ROOMS_LIMIT: int = 2


def main(args: list[str]) -> None:
    launch_check(args)
    receive_thread = threading.Thread(target=receive_data)
    receive_thread.daemon = True
    receive_thread.start()
    prompt_message()


if __name__ == "__main__":
    main(sys.argv[1:])
