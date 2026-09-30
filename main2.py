from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional

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


