from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
app= FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials= True,
    allow_headers=["*"],
    allow_methods=["*"]
)

class SideState(BaseModel):
    owner:Optional[bool]= None
    sideSelected: bool= False

class Squares(BaseModel):
    owner: Optional[bool]= False
    numselected: int
    SideBot: SideState
    SideLeft: SideState
    SideRight: SideState
    SideTop:SideState


class GameState(BaseModel):
    players2Turn:bool
    ScoreQwen: int
    ScoreGemma:int
    squares:List[List[Squares]]


class Agent:
    def __init__(self,name, model,tokenizer):
        self.name= name
        self.model= model
        self.tokenizer= tokenizer





qwen= "Qwen/Qwen2.5-7B-Instruct"
gemma= "google/gemma-3-4b-it"

qwen_tokenizer= AutoTokenizer.from_pretrained(qwen)
qwen_model= AutoModelForCausalLM(
    qwen,
    torch_dtype="auto",
    device_type="auto"
)


gemma_tokenizer= AutoTokenizer.from_pretrained(gemma)
gemma_model= AutoModelForCausalLM(
    gemma,
    torch_dtype="auto",
    device_dtype="auto"
)

print("Loading Qwen...")

QWEN= Agent(
    "Qwen",
    qwen_model,
    qwen_tokenizer
)


print("Loading Gemma...")
GEMMA= Agent(
    "Gemma",
    gemma_model,
    gemma_tokenizer
)


def get_available_moves(squares):
    """Finds a'' unselected moves sides in the grid"""
    available=[]
    rows=len(squares)
    cols= len(squares[0])

    for r in range(rows):
        for c in range(cols):
            sq= squares[r][c]

            if not sq.sideTop.selected:
                available.append({"row":r, "col":c, "side": "TOP"})

            if not sq.sideBot.selected:
                available.append({"row":r, "col":c, "side":"BOTTOM"})

            if not sq.sideRight.selected:
                available.append({"row":r, "col":c, "side": "RIGHT"})

            if not sq.sideLeft.selected:
                available.append({"row":r, "col":c, "side": "LEFT"})

    unique_moves=[]
    seen= set()

    for move in available:
        r,c,s= move["row"], move["col"], move["side"]
        key= f"{r},{c},{s}"

        if s=="RIGHT" and c+1< cols:
            key= f"{r},{c+1},LEFT"

        if s=="BOT" and r+1< rows:
            key= f"{r+1},{c},TOP"


        if key not in seen:
            seen.add(key)
            unique_moves.append(move)

    return unique_moves


@app.post("/game-state")

async def get_game_state(state:GameState):
    """Get Real time game state """

    #Determine which model takes action for this turn
    if state.players2Turn:
        agent= QWEN
    else:
        agent= GEMMA

    available_moves= get_available_moves(state.squares)
