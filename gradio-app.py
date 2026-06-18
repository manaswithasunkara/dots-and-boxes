import gradio as gr
import json, random, shutil

shutil.copy("/assets/game.html", "/tmp/game.html")

GRID = 5

GEMMA_SYS = (
    "You are Gemma, a bold and creative Google AI playing Dots & Boxes. "
    "You are inventive, a little cheeky, and love claiming boxes. "
    "You are Player G on the board."
)
QWEN_SYS = (
    "You are Qwen, a precise and methodical Alibaba AI playing Dots & Boxes. "
    "You think carefully, avoid gifting chains to the opponent, and have dry wit. "
    "You are Player Q on the board."
)

MOVE_PROMPT = """Board (G=Gemma box, Q=Qwen box, blank=unclaimed):
{board}

Available moves: {moves}
Your score: {my} | Opponent score: {opp}

Grab a box if you can. Don't leave 3-sided boxes open for opponent.

/no_think
Reply ONLY with this JSON, nothing else:
{{"move": "h(2,3)", "thought": "one punchy sentence"}}"""

# ── Board logic ───────────────────────────────────────────────
def empty_board():
    return {
        "h":      [[False]*GRID for _ in range(GRID+1)],
        "v":      [[False]*(GRID+1) for _ in range(GRID)],
        "owners": [[None]*GRID for _ in range(GRID)],
        "scores": [0, 0],
        "turn":   0,
    }

def get_moves(board):
    m = []
    for r in range(GRID+1):
        for c in range(GRID):
            if not board["h"][r][c]: m.append(("h",r,c))
    for r in range(GRID):
        for c in range(GRID+1):
            if not board["v"][r][c]: m.append(("v",r,c))
    return m

def fill_boxes(board, t, r, c):
    done, p = 0, board["turn"]
    h, v, own = board["h"], board["v"], board["owners"]
    def closed(br, bc):
        return h[br][bc] and h[br+1][bc] and v[br][bc] and v[br][bc+1]
    if t == "h":
        for br in [r-1, r]:
            if 0<=br<GRID and 0<=c<GRID and closed(br,c) and own[br][c] is None:
                own[br][c]=p; board["scores"][p]+=1; done+=1
    else:
        for bc in [c-1, c]:
            if 0<=r<GRID and 0<=bc<GRID and closed(r,bc) and own[r][bc] is None:
                own[r][bc]=p; board["scores"][p]+=1; done+=1
    return done

def apply_move(board, move):
    t, r, c = move
    board[t][r][c] = True
    done = fill_boxes(board, t, r, c)
    if done == 0:
        board["turn"] = 1 - board["turn"]
    return done

def board_ascii(board):
    rows = []
    h, v = board["h"], board["v"]
    for r in range(GRID+1):
        row = "".join("+" + ("---" if h[r][c] else "   ") for c in range(GRID)) + "+"
        rows.append(row)
        if r < GRID:
            row2 = ""
            for c in range(GRID+1):
                row2 += "|" if v[r][c] else " "
                if c < GRID:
                    o = board["owners"][r][c]
                    row2 += " {} ".format("G" if o==0 else "Q" if o==1 else " ")
            rows.append(row2)
    return "\n".join(rows)

def moves_str(moves):
    return ", ".join(f"{t}({r},{c})" for t,r,c in moves[:20])

def safe_move(board, moves):
    def gives_away(m):
        t, r, c = m
        h = [row[:] for row in board["h"]]
        v = [row[:] for row in board["v"]]
        if t=="h": h[r][c]=True
        else:      v[r][c]=True
        for br in range(GRID):
            for bc in range(GRID):
                if board["owners"][br][bc] is None:
                    s = sum([h[br][bc], h[br+1][bc], v[br][bc], v[br][bc+1]])
                    if s == 3: return True
        return False
    safe = [m for m in moves if not gives_away(m)]
    return random.choice(safe) if safe else random.choice(moves)

def parse_move(raw, moves):
    text = raw.strip()
    if "<think>" in text:
        end = text.find("</think>")
        text = text[end+8:].strip() if end != -1 else text
    if "```" in text:
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else parts[0]
        if text.startswith("json"): text = text[4:]
    text  = text.strip()
    start = text.find("{")
    end   = text.rfind("}") + 1
    if start >= 0 and end > start:
        text = text[start:end]
    try:
        data    = json.loads(text)
        ms      = data["move"].strip()
        thought = data.get("thought", "...")
        t       = ms[0]
        nums    = ms[2:-1].split(",")
        move    = (t, int(nums[0].strip()), int(nums[1].strip()))
        return (move, thought) if move in moves else (None, thought)
    except Exception:
        return None, None

_gemma_fn = None
_qwen_fn  = None

def ask_model(board, player):
    global _gemma_fn, _qwen_fn
    # Lazy init — only look up Modal functions when first move is made
    if _gemma_fn is None or _qwen_fn is None:
        import modal
        GemmaCls = modal.Cls.from_name("dots-and-boxes-llamacpp", "GemmaServer")
        QwenCls  = modal.Cls.from_name("dots-and-boxes-llamacpp", "QwenServer")
        _gemma_fn = GemmaCls()
        _qwen_fn  = QwenCls()

    moves  = get_moves(board)
    prompt = MOVE_PROMPT.format(
        board=board_ascii(board),
        moves=moves_str(moves),
        my =board["scores"][player],
        opp=board["scores"][1-player],
    )
    sys_p = GEMMA_SYS if player==0 else QWEN_SYS
    fn    = _gemma_fn  if player==0 else _qwen_fn
    raw   = fn.generate.remote(sys_p, prompt)
    move, thought = parse_move(raw, moves)
    if move is None:
        move    = safe_move(board, moves)
        thought = (thought or "Hmm...") + " (move adjusted)"
    return move, thought

# ── UI helpers ────────────────────────────────────────────────
def bubble(name, text, color, align):
    side = "flex-end" if align == "right" else "flex-start"
    bg   = "#1b1b35" if align == "left"  else "#0f2820"
    return (
        f'<div style="display:flex;justify-content:{side};margin:5px 0;">'
        f'<div style="max-width:83%;background:{bg};border-left:3px solid {color};'
        f'border-radius:8px;padding:8px 12px;font-size:13px;color:#eee;line-height:1.5;">'
        f'<b style="color:{color}">{name}</b><br>{text}</div></div>'
    )

def chat_div(history):
    if not history:
        return '<div style="color:#888;padding:12px;">Press Start to watch the models battle!</div>'
    return "".join(bubble(e["name"],e["text"],e["color"],e["align"]) for e in history[-22:])

def score_html(board):
    g, q  = board["scores"]
    total = GRID * GRID
    done  = g + q
    t     = board["turn"]
    if done >= total:
        label = "🎉 Gemma wins!" if g>q else "🎉 Qwen wins!" if q>g else "🤝 Draw!"
    else:
        label = "⏳ Gemma 🌸 thinking..." if t==0 else "⏳ Qwen 🐉 thinking..."
    return (
        f'<div style="text-align:center;font-size:15px;font-weight:bold;'
        f'padding:8px;background:#12122a;border-radius:6px;color:#eee;margin-bottom:6px;">'
        f'Gemma 🌸: {g} &nbsp;|&nbsp; Qwen 🐉: {q}'
        f'&nbsp;—&nbsp; {label} &nbsp;({done}/{total} boxes)</div>'
    )

def relay_js(move, board, completed):
    t, r, c     = move
    just_played = board["turn"] if completed else 1 - board["turn"]
    payload     = json.dumps({
        "type": "move", "t": t, "r": r, "c": c,
        "player":    just_played,
        "scorep1":   board["scores"][0],
        "scorep2":   board["scores"][1],
        "next_turn": board["turn"],
    })
    return (
        f"<script>(function(){{"
        f"var f=document.getElementById('gf');"
        f"if(f)f.contentWindow.postMessage({payload},'*');"
        f"}})();</script>"
    )

IFRAME = (
    '<iframe id="gf" src="/gradio_api/file=/tmp/game.html" '
    'width="450" height="530" '
    'style="border:none;border-radius:8px;display:block;margin:0 auto;" '
    'scrolling="no"></iframe>'
)
CSS = "#chat{height:460px;overflow-y:auto;background:#0a0a1a;border-radius:8px;padding:10px;border:1px solid #22224a;}"

# ── Gradio UI ─────────────────────────────────────────────────
with gr.Blocks(title="Dots & Boxes: Gemma 4 vs Qwen3", css=CSS) as demo:

    board_st   = gr.State(empty_board())
    hist_st    = gr.State([])
    is_running = gr.State(False)

    gr.Markdown("# 🎮 Dots & Boxes — Gemma 4 🌸 vs Qwen3 🐉")
    gr.Markdown("**Gemma-4-4B-it** vs **Qwen3-4B** — both on Modal T4 GPUs via llama.cpp.")

    with gr.Row():
        with gr.Column(scale=5):
            score_bar = gr.HTML(score_html(empty_board()))
            gr.HTML(IFRAME)
            relay     = gr.HTML("")
        with gr.Column(scale=4):
            gr.Markdown("### 💬 Model Thoughts")
            chat_html = gr.HTML(f'<div id="chat">{chat_div([])}</div>')

    with gr.Row():
        start_btn = gr.Button("▶ Start Game",   variant="primary",   scale=2)
        reset_btn = gr.Button("🔄 Reset Board",  variant="secondary", scale=1)
        with gr.Column(scale=3):
            status = gr.Markdown("Press **Start Game** to begin.")

    def do_reset():
        b  = empty_board()
        js = (
            "<script>(function(){var f=document.getElementById('gf');"
            "if(f)f.contentWindow.postMessage({type:'reset'},'*');})();</script>"
        )
        return b, [], score_html(b), f'<div id="chat">{chat_div([])}</div>', js, "Board reset!", False

    def do_step(board, history, running):
        if not running:
            return (board, history, score_html(board),
                    f'<div id="chat">{chat_div(history)}</div>', "", gr.skip())
        total = GRID * GRID
        if board["scores"][0] + board["scores"][1] >= total:
            return (board, history, score_html(board),
                    f'<div id="chat">{chat_div(history)}</div>', "", "Game over!")
        player = board["turn"]
        name   = "Gemma 🌸" if player==0 else "Qwen 🐉"
        color  = "#f48fb1"  if player==0 else "#4ecdc4"
        align  = "left"     if player==0 else "right"
        try:
            move, thought = ask_model(board, player)
        except Exception as e:
            import traceback
            traceback.print_exc()   # prints full error to Modal logs
            moves   = get_moves(board)
            move    = safe_move(board, moves)
            thought = f"Error: {str(e)[:80]} — safe move"
        completed = apply_move(board, move)
        t, r, c   = move
        sym       = "↔" if t=="h" else "↕"
        msg = (
            f"{thought}<br>"
            f"<small style='opacity:0.5'>→ {sym}({r},{c})"
            + (f" &nbsp;✅ {completed} box{'es' if completed>1 else ''}!" if completed else "")
            + "</small>"
        )
        history = history + [{"name":name,"text":msg,"color":color,"align":align}]
        done2 = board["scores"][0] + board["scores"][1]
        if done2 >= total:
            g, q = board["scores"]
            if g > q:
                history.append({"name":"Gemma 🌸","text":"Google wins again 😄","color":"#f48fb1","align":"left"})
            elif q > g:
                history.append({"name":"Qwen 🐉","text":"Methodical beats flashy 🎯","color":"#4ecdc4","align":"right"})
            else:
                history.append({"name":"Gemma 🌸","text":"A draw?! Didn't see that coming 👀","color":"#f48fb1","align":"left"})
        js = relay_js(move, board, completed)
        return (board, history, score_html(board),
                f'<div id="chat">{chat_div(history)}</div>', js, "Playing...")

    def start_game():
        return "⏳ First move incoming...", True

    timer = gr.Timer(value=15)

    start_btn.click(start_game, outputs=[status, is_running])

    reset_btn.click(do_reset,
        outputs=[board_st, hist_st, score_bar, chat_html, relay, status, is_running])

    timer.tick(do_step,
        inputs=[board_st, hist_st, is_running],
        outputs=[board_st, hist_st, score_bar, chat_html, relay, status])

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import gradio as gr
import uvicorn

# 1. Create your base FastAPI app
fastapi_app = FastAPI()

# 2. Setup your Gradio blocks / interface
# (Ensure your 'demo' variable is defined above this line)

# 3. Mount the Gradio application to your path
demo.allowed_paths = ["/tmp"]
fastapi_app = gr.mount_gradio_app(
    fastapi_app,
    demo,
    path="/",
    root_path="https://manaswitha-sunkara--dots-and-boxes.modal.run",
    allowed_paths=["/tmp"],
)

# 4. FIX: Apply CORS middleware to the *final* wrapped application.
# This ensures that ALL routes (including Gradio's internal ones) get CORS headers.
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://manaswitha-sunkara--dots-and-boxes-dev.modal.run",
        "https://manaswitha-sunkara--dots-and-boxes.modal.run"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 5. Run the server
uvicorn.run(fastapi_app, host="0.0.0.0", port=7860)
