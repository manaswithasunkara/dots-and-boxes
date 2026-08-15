from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch


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
    scoreComp:int
    scorePlay:int
    squares: List[List[SquareState]]


class Move(BaseModel):
    row: int
    col: int
    side: str


class MoveResponse(BaseModel):
    agent: str
    move:Move
    message:str





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

            if not r==grid_size-1 and not sq.sideBot.sideSelected:
                moves.append(Move(row=r, col=c, side="bot"))

            if not c==grid_size-1 and not sq.sideRight.sideSelected:
                moves.append(Move(row=r, col=c, side="right"))

    return moves


@app.post("/game-state")
async def receive_game_state(state: GameState):

    moves= available_moves(state)

    print("Available moves")

    for i,move in enumerate(moves):
        print(i,move)

    print("received game state")
    print(state)

    return{
        "status": "Success",
        "available_moves": moves
    }







