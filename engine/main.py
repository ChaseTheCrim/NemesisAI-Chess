import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import chess

from nemesis.trainer  import NemesisTrainer
from nemesis.selector import select_move

def main():
    board   = chess.Board()
    nemesis = NemesisTrainer()

    print("[NEMESIS] Engine ready.", file=sys.stderr, flush=True)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        if line == "quit":
            break

        try:
            move = chess.Move.from_uci(line)
            if move not in board.legal_moves:
                _respond({"status": "illegal", "message": "Bu hamle kurallara aykırı!"})
                continue

            nemesis.on_player_move(board, move)
            board.push(move)

            game_over = _check_game_over(board)
            if game_over:
                _respond({
                    "status":    "legal",
                    "fen":       board.fen(),
                    "turn":      "black" if board.turn == chess.BLACK else "white",
                    "game_over": game_over,
                })
                continue

            player_read  = nemesis.predict_player(board)
            nemesis_move = select_move(board, player_read, nemesis.evaluator)

            if nemesis_move:
                board.push(nemesis_move)

            game_over = _check_game_over(board)
            response  = {
                "status":  "legal",
                "fen":     board.fen(),
                "turn":    "black" if board.turn == chess.BLACK else "white",
                "ai_move": nemesis_move.uci() if nemesis_move else "",
            }
            if game_over:
                response["game_over"] = game_over
            _respond(response)

        except Exception as e:
            print(f"[NEMESIS HATA]: {e}", file=sys.stderr, flush=True)
            _respond({"status": "error", "message": str(e)})

    nemesis.close()


def _check_game_over(board: chess.Board):
    if board.is_checkmate():
        return "checkmate"
    if board.is_stalemate():
        return "stalemate"
    if board.is_insufficient_material():
        return "draw_material"
    if board.is_fifty_moves():
        return "draw_fifty"
    if board.is_repetition(3):
        return "draw_repetition"
    return None


def _respond(data: dict):
    print(json.dumps(data), flush=True)


if __name__ == "__main__":
    main()