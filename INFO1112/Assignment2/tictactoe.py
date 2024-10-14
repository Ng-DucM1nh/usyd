BOARD_SIZE = 3
CELL_SIZE = 5
ROW_SEPARATOR = '-'
N_ROW_SEPARATORS = CELL_SIZE + (CELL_SIZE - 1) * (BOARD_SIZE - 1)
COLUMN_SEPARATOR = '|'

Board = list[list[str]]

def create_board() -> Board:
    """Create and return an empty board"""
    return [[' ' for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]


def print_board(board: Board) -> None:
    """Print the board to stdout"""
    print(ROW_SEPARATOR * N_ROW_SEPARATORS)
    for row in board:
        for value in row:
            print(f"{COLUMN_SEPARATOR} {value} ", end='')
        print(COLUMN_SEPARATOR)
        print(ROW_SEPARATOR * N_ROW_SEPARATORS)


def get_board_status(board: Board) -> str:
    """Convert the board to a status code and return it"""
    ans: str = ""
    for i in range(BOARD_SIZE):
        for j in range(BOARD_SIZE):
            if board[i][j] == ' ':
                ans += "0"
            elif board[i][j] == 'X':
                ans += "1"
            elif board[i][j] == 'O':
                ans += "2"
    return ans


def get_marker(board: Board, row: int, col: int) -> str | None:
    """Get the marker at position (<row>,<col>) on the board"""
    if row < 0 or row > 2 or col < 0 or col > 2:
        print(f"Invalid position ({row},{col}). Row/Column must be an integer between 0 and 2")
        return
    return board[row][col]


def put_marker(board: Board, row: int, col: int, marker: str) -> Board | None:
    """Put the marker <marker> at position (<row>,<col>) on the board"""
    if row < 0 or row > 2 or col < 0 or col > 2:
        print(f"Invalid position ({row},{col}). Row/Column must be an integer between 0 and 2")
        return
    if get_marker(board, row, col) != ' ':
        print(f"({row},{col}) is occupied by {board[row][col]}")
        return
    if marker not in ('X', 'O'):
        print("marker must be X or O")
        return
    board[row][col] = marker
    return board


def player_wins_vertically(player: str, board: Board) -> bool:
    """Check if <player> wins vertically"""
    return any(
        all(board[y][x] == player for y in range(BOARD_SIZE))
        for x in range(BOARD_SIZE)
    )


def player_wins_horizontally(player: str, board: Board) -> bool:
    """Check if <player> wins horizontally"""
    return any(
        all(board[x][y] == player for y in range(BOARD_SIZE))
        for x in range(BOARD_SIZE)
    )


def player_wins_diagonally(player: str, board: Board) -> bool:
    """Check if <player> wins diagonally"""
    return (
        all(board[y][y] == player for y in range(BOARD_SIZE)) or
        all(board[BOARD_SIZE - 1 - y][y] == player for y in range(BOARD_SIZE))
    )


def player_wins(player: str, board: Board) -> bool:
    """Determines whether the specified player wins given the board"""
    return (
        player_wins_vertically(player, board) or
        player_wins_horizontally(player, board) or
        player_wins_diagonally(player, board)
    )


def players_draw(board: Board) -> bool:
    """Determines whether the players draw on the given board"""
    return all(
        board[y][x] != ' '
        for y in range(BOARD_SIZE)
        for x in range(BOARD_SIZE)
    )


def assign_board(status: str) -> Board:
    """Create and return a board that matches the given status code <status>"""
    board = create_board()
    for i in range(BOARD_SIZE):
        for j in range(BOARD_SIZE):
            if status[3*i + j] == "0":
                board[i][j] = ' '
            elif status[3*i + j] == "1":
                board[i][j] = 'X'
            elif status[3*i + j] == "2":
                board[i][j] = 'O'
    return board


def main() -> None:
    board = create_board()
    print_board(board)
    game_won = game_drawn = False
    player = 'X'
    while not game_won and not game_drawn:
        while True:
            print(f"You are {player}. Place your marker")
            try:
                row = int(input("Row: "))
                col = int(input("Col: "))
            except Exception as e:
                print(f"caught exception {e}")
                continue
            if row < 0 or row > 2 or col < 0 or col > 2:
                print(f"Invalid position ({row},{col}). Row/Column must be an integer between 0 and 2")
            elif get_marker(board, row, col) != ' ':
                print(f"({row},{col}) occupied by {board[row][col]}")
            else:
                break
        board = put_marker(board, row, col, player)
        print_board(board)
        if player_wins(player, board):
            print(f"{player} wins the game!")
            return
        if players_draw(board):
            print("The game draws!")
            return
        player = 'X' if player == 'O' else 'O'


if __name__ == "__main__":
    main()
