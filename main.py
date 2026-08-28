from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import re


app= FastAPI()

QWEN_MODEL= "Qwen/Qwen2.5-7B-Instruct"
GEMMA_MODEL= "google/gemma-3-4b-it"


print("Loading Qwen")
qwen_tokenizer= AutoTokenizer.from_pretrained(QWEN_MODEL)

qwen_model= AutoModelForCausalLM.from_pretrained(
    QWEN_MODEL,
    torch_dtype= "auto",
    device_map= "auto"
)

print("Qwen  loaded!")

gemma_tokenizer= AutoTokenizer.from_pretrained(GEMMA_MODEL)
gemma_model= AutoModelForCausalLM.from_pretrained(
    GEMMA_MODEL,
    torch_dtype="auto",
    device_map="auto"
)

class SideState(BaseModel):
    owner:Optional[bool]= None
    sideSelected: bool= False

class SquareState(BaseModel):
    owner: Optional[bool]=None
    numSelected: int
    sideBot: SideState
    sideLeft: SideState
    sideRight: SideState
    sideTop: SideState

class GameState(BaseModel):
    players2Turn:bool
    scoreQwen:int
    scoreGemma:int
    squares: List[List[SquareState]]


class Move(BaseModel):
    row: int
    col: int
    side: str


class MoveResponse(BaseModel):
    agent: str
    move:Move
    message:str


class Agent:
    def __init__(self, name, model, tokenizer):
        self.name= name
        self.model= model
        self.tokenizer= tokenizer

    def generate(self,prompt:str):

        messages= [
            {"role": "System",
              "content": ("You are an expert Dots and Boxes Player,"
                         "choose the best move from legal moves provided"
                          )
             },
            {
                "role": "user",
                "content":prompt
            }
        ]


        text= self.tokenizer.apply_chat_template(
            messages, tokenize=False,  add_generation_prompt=True
        )

        inputs= self.tokenizer(
            text,
            return_tensors="pt"
        )

        # Move inputs to same device as model
        inputs={
            key: value.to(self.model.device)
            for key, value in inputs.items()
        }

        with torch.no_grad():
            outputs= self.generate(**inputs,
                                   max_new_token=20,
                                   do_sample=False)

        generated_tokens= outputs[0,
        inputs["input_ids"].shape[1]:
        ]
        response= self.tokenizer.decode(
            generated_tokens,
            skip_special_tokens=True
        )

        return response.strip()


    def choose_move(self, state: GameState, moves: List[Move]):

        prompt= build_game_prompt(
            state,
            moves,
            self.name
        )

        print(f"\n========= {self.name} PROMPT =============")
        print(prompt)


        response= self.generate(prompt)

        print(f"\n============= {self.name} RESPONSE =============")
        print(response)

        move_index= parse_move_index( response, len(moves))

        return moves[move_index]








qwen_agent= Agent(
    "Qwen",
    qwen_model,
    qwen_tokenizer
)

gemma_agent= Agent(
    "Gemma",
    gemma_model,
    gemma_tokenizer
)







app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials= True,
    allow_methods= ["*"],
    allow_headers=["*"]
)





def build_game_prompt(
        state: GameState,
        moves: List[Move],
        agent_name: str
):
    if agent_name=="Qwen":
        my_score= state.scoreComp
        opponent_score= state.scorePlay

    else:
        my_score= state.scorePlay
        opponent_score= state.scorePlay

    legal_moves= "\n".join(
        f"{i}: row={move.row}, col={move.col}, side={move.side}"
        for i, move in enumerate(moves)
    )

    prompt= (f"You re playing Dots and Boxes as {agent_name}."
             f"Your score : {my_score}"
             f"Opponent score: {opponent_score}"
             f"You must choose ONE move from legal moves below."
             f"LEGAL MOVES:"
             f"{legal_moves}"
             f"Return only the number corresponding to your choose move"
             f"for example:"
             f"3"
             f"Do not provide an explanation")

    return  prompt


def ask_qwen(prompt: str):
    messages=[
        {
            "role": "system",
            "content": prompt
        }
    ]


def available_moves(state:GameState):
    grid_size= len(state.squares)
    moves=[]
    for r in range(grid_size):
        for c in range(grid_size):
            sq= state.squares[r][c]
            if not sq.sideTop.sideSelected:
                moves.append(Move(row=r, col=c, side="top"))
            if not sq.sideLeft.sideSelected:
                moves.append(Move(row=r,col=c, side="left"))

            if r==grid_size-1 :
                if not sq.sideBot.sideSelected:
                    moves.append(Move(row=r, col=c, side="bot"))

            if c==grid_size-1 :
                if not sq.sideRight.sideSelected:
                    moves.append(Move(row=r, col=c, side="right"))

    return moves



def parse_move_index(response: str, num_moves: int)-> int:

    match= re.search(r"\b\d+\b", response)

    if not match:
        raise ValueError(
            f"Could not parse move from {response}"
        )

    move_index= int(match.group())

    if move_index < 0 or move_index>= num_moves:
        raise ValueError(
            f"Invalid move index: {move_index}"
        )

    return move_index



def get_side(square:SquareState, side:str)-> SideState:
    if side == "top":
        return square.sideTop
    if side== "left":
        return square.sideLeft
    if side== "right":
        return square.sideRight
    if side == "bot":
        return square.sideBot

    raise ValueError(f"Unknown side: {side}")


def apply_move(state: GameState, move: Move, agent:str):


    square= state.squares[move.row][move.col]
    side= get_side(square, move.side)

    if side.sideSelected:
        raise ValueError("Move has already been selected")

    side.sideSelected= True

    # store who selected
    if agent== "Qwen":
        side.owner= True
    else:
        side.owner=False

    completed= square_completed(square)

    if completed:
        if square.owner is not None:
            raise ValueError("Square already as an owner")

        if agent == "Qwen":
            state.scoreQwen+=1
            square.owner=True

        else:
            state.scoreGemma+=1
            square.owner=False


    return completed



def update_neighbor(state: GameState, move: Move, agent:str):

    r= move.row
    c= move.col

    if move.side== "top":
        #Neighbor above
        if r>0:
            neighbor= state.squares[r-1][c]
            neighbor.sideBot.sideSelected= True

            if agent=="Qwen":
                neighbor.sideBot.owner= True
            else:
                neighbor.sideBot.owner= False

    elif move.side== "left":
        if  c>0:
            neighbor= state.squares[r][c-1]
            neighbor.sideRight.sideSelected= True

            if agent=="Qwen":
                neighbor.sideRight.owner= True
            else:
                neighbor.sideRight.owner= False

    elif move.side== "right":
        if c>0:
            neighbor= state.squares[r][c+1]
            neighbor.sideLeft.sideSelected= True

            if agent== "Qwen":
                neighbor.sideLeft.owner= True
            else:
                neighbor.sideLeft.owner=False

    elif move.side== "bot":
        # Neighbor below
        if r< len(state.squares)-1:
            neighbor= state.squares[r+1][c]
            neighbor.sideTop.sideSelected= True

            if agent=="Qwen":
                neighbor.sideTop.owner=True
            else:
                neighbor.sideTop.owner= False


def square_completed(square: SquareState)-> bool:
    return(
        square.sideTop.sideSelected
        and square.sideBot.sideSelected
        and square.sideLeft.sideSelected
        and square.sideRight.sideSelected
    )


def set_side_owner(side:SideState, agent:str):

    side.sideSelected= True

    if agent==" Qwen":
        side.owner= True

    else:
        side.owner=False



@app.post("/game-state")
async def receive_game_state(state: GameState):

    moves= available_moves(state)

    if not moves:
        return {
            "status": "game_over",
            "message": "No moves remaining"
        }

    # Temporary mapping
    if state.players2Turn:
        agent= qwen_agent
    else:
        agent= gemma_agent

    print(f"\n {agent.name}'s turn")
    print(f"Available moves {len(moves)}")


    selected_move= agent.choose_move(
        state,
        moves
    )

    print(
        f"{agent.name} selected:"
        f"{selected_move}"
    )

    completed= apply_move(state, selected_move, agent.name)

    if not completed:
        state.players2Turn= not state.players2Turn

    return{
        "status": "Success",
        "agent": agent.name,
        "moves": selected_move,
        "completed_square":completed,
        "scoreQwen": state.scoreQwen,
        "scoreGemma": state.scoreGemma,
        "players2Turn": state.players2Turn
    }







