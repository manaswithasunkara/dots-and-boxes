//  game parameters
const DELAY_END= 2; // seconds until new game starts
const HEIGHT= 550;
const FPS= 30;
const GRID_SIZE= 5;

// Derived parameters
const WIDTH= HEIGHT*0.9;
const CELL= WIDTH/(GRID_SIZE +2); // size of the cells as well as left and right margin
const STROKE= CELL/12;
const DOT= STROKE; // dot radius
const MARGIN = HEIGHT - (GRID_SIZE +1)* CELL ;//top margin for score, names, etc




// Set up the game canvas
const canvas= document.getElementById("game-canvas");
canvas.height= HEIGHT;
canvas.width= WIDTH;

var canvRect= canvas.getBoundingClientRect()



// set up context
var ctx= canvas.getContext("2d");
ctx.lineWidth= STROKE;
ctx.textAlign= "center";
ctx.textBaseline= "middle";


//  game variables
let  playersTurn= true;
let squares=[];
let scorep1=0;
let scorep2=0;
let timeEnd=0;
let gameActive=false;


// event handlers
canvas.addEventListener("mousemove", highlightGrid);
canvas.addEventListener("click", click);

// set up the game loop
setInterval(loop, 1000/FPS);

// colours
const COLOR_BOARD= "cornsilk";
const COLOR_BORDER= "wheat";
const COLOR_DOT= "sienna";
const COLOR_PLAY1= "crimson";
const COLOR_PLAY1_LIT= "lightpink";
const COLOR_PLAY2= "royalblue";
const COLOR_PLAY2_LIT= "lightsteelblue";
const COLOR_TIE= "black";


// text
const TEXT_PLAYER1= "Llama3.2-3B";
const TEXT_P1_SML= "P1";
const TEXT_PLAYER2= "Qwen2.5-3B";
const TEXT_P2_SMALL= "P2";
const TEXT_SIZE_CELL= CELL /3;
const TEXT_SIZE_TOP= MARGIN/6;
const TEXT_TIE= "DRAW!!";
const TEXT_WIN_P1= "PLAYER 1 WINS!";
const TEXT_WIN_P2= "PLAYER 2 WINS!";


// definitions
const Side={
    BOT:0,
    LEFT:1,
    RIGHT:2,
    TOP: 3
}



function loop(){
    drawBoard();
    drawSquares()
    drawGrid();
    drawScores();
}

// function click(/** @type {MouseEvent} */ ev){
//     if (timeEnd>0){
//         return;
//     }
//     selectSide();
// }

function drawBoard(){
    ctx.fillStyle= COLOR_BOARD;
    ctx.strokeStyle= COLOR_BORDER;
    ctx.fillRect(0,0, WIDTH, HEIGHT);
    ctx.strokeRect(STROKE/2, STROKE/2, WIDTH-STROKE, HEIGHT-STROKE );
}

function drawDot(x,y ){
    ctx.fillStyle= COLOR_DOT;
    ctx.beginPath();
    ctx.arc(x,y,DOT,0,Math.PI *2);
    ctx.fill();
}

function getColor(player1, light){
    if (player1){
        return light ? COLOR_PLAY1_LIT: COLOR_PLAY1;
    } else {
        return light ? COLOR_PLAY2_LIT: COLOR_PLAY2;
    }
}

function getText(player1, small){
    if (player1){
        return small? TEXT_P1_SML: TEXT_PLAYER1;
    }else{
        return small? TEXT_P2_SMALL: TEXT_PLAYER2;
    }
}

function getGridX(col){
    return CELL *(col+1);
}

function getGridY(row){
    return MARGIN + CELL *row;
}

// function highlightGrid(/** @type {MouseEvent}*/ ev){
// //     get mouse position relative to the canvas
//     let x= ev.clientX- canvRect.left;
//     let y= ev.clientY-canvRect.top;
//
// //     highlight the squares side
//     highlightSide(x,y);
// }
//
// function highlightSide(x,y){
// //     clear previous highlighting
//     for (let row of squares){
//         for (let square of row){
//             square.highlight= null;
//         }
//     }
//     // check each cell
//     let rows= squares.length;
//     let cols= squares[0].length;
//     currentCells=[];
//     OUTER: for ( let i=0; i< rows; i++){
//         for (let j=0; j<cols; j++){
//             if (squares[i][j].contains(x,y)){
//                 let side= squares[i][j].highlightSide(x,y);
//                 if(side!=null){
//                     currentCells.push({row: i, col:j})
//                 }
//
//                 // determine neighbor
//                 let row= i, col= j, highlight, neighbour= true;
//                 if(side== Side.LEFT && j>0){
//                     col=j-1;
//                     highlight= Side.RIGHT;
//                 }
//                 else if(side== Side.RIGHT && j< cols-1){
//                     col=j+1;
//                     highlight= Side.LEFT;
//                 }
//                 else if(side== Side.TOP && i>0){
//                     row=i-1;
//                     highlight= Side.BOT;
//                 }
//                 else if(side== Side.BOT && i< rows-i){
//                     row=i+1;
//                     highlight= Side.TOP;
//                 } else{
//                     neighbour= false;
//                 }
//
//
//                 // highlight neighbor
//
//                 if(neighbour){
//                     squares[row][col].highlight= highlight;
//                     currentCells.push({row:row, col:col});
//                 }
//                 // there is no need to continue
//                 break OUTER;
//             }
//         }
//     }
// }

function drawGrid(){
    for (let i =0; i< GRID_SIZE +1; i++){
        for (let j=0; j< GRID_SIZE +1; j++){
            drawDot(getGridX(j), getGridY(i));
        }
    }
}

function drawLine(x0, y0, x1, y1, color){
    ctx.strokeStyle= color;
    ctx.beginPath();
    ctx.moveTo(x0, y0);
    ctx.lineTo(x1, y1);
    ctx.stroke()
}

function drawScores(){
    let colP1= playersTurn? COLOR_PLAY1: COLOR_PLAY1_LIT;
    let colP2= playersTurn? COLOR_PLAY2_LIT: COLOR_PLAY2;
    drawText(TEXT_PLAYER1, WIDTH * 0.25, MARGIN *0.25, colP1, TEXT_SIZE_TOP);
    drawText(scorep1, WIDTH * 0.25, MARGIN *0.6, colP1, TEXT_SIZE_TOP*2);
    drawText(TEXT_PLAYER2, WIDTH * 0.75, MARGIN *0.25, colP2, TEXT_SIZE_TOP);
    drawText(scorep2, WIDTH * 0.75, MARGIN *0.6, colP2, TEXT_SIZE_TOP*2);

    // // GAME OVER TEXT
    // if(timeEnd >0){
    //     timeEnd--;
    //
    // //     handle a tie
    //     if (scorep2== scorep1){
    //         drawText(TEXT_TIE, WIDTH*0.5, MARGIN * 0.6, COLOR_TIE, TEXT_SIZE_TOP);
    //     }else{
    //             let p1Wins= scorep1> scorep2;
    //             let color= p1Wins? COLOR_PLAY1: COLOR_PLAY2;
    //             let text= p1Wins? TEXT_WIN_P1: TEXT_WIN_P2;
    //             drawText(text, WIDTH*0.5, MARGIN * 0.6, color, TEXT_SIZE_TOP);
    //     }
    //
    // //      new game
    //     if (timeEnd==0){
    //         newGame();
    //     }
    // }
}


function drawSquares(){
    for (let row of squares){
        for (let square of row){
            square.drawSides()
            square.drawFill()
        }
    }

}

function drawText(text, x, y, color, size){
    ctx.fillStyle= color;
    ctx.font= size + "px dejavu sans mono";
    ctx.fillText(text, x,y);
}

// create the square object constructor

function newGame(){
    currentCells=[];
    playersTurn= Math.random() >= 0.5;
    scorep1= 0;
    scorep2=0;
    timeEnd=0;



//     set up the squares
    squares= [];
    for (let i =0; i< GRID_SIZE; i++){
        squares[i]=[];
        for (let j =0; j< GRID_SIZE; j++){
            squares[i][j]= new Square(getGridX(j), getGridY(i), CELL, CELL);
        }
    }
}

// function selectSide(){
//
//     if(currentCells== null || currentCells.length ==0){
//         return;
//     }
//     // select the sides(s)
//
//     let filledSquare = false;
//
//     for(let cell of currentCells){
//         if (squares[cell.row][cell.col].selectSide()){
//             filledSquare= true;
//         }
//     }
//     currentCells = [];
//
// //     check for winner
//     if (filledSquare){
//         if (scorep1 + scorep2 == GRID_SIZE *GRID_SIZE){
//            //   gAME oVER
//            timeEnd= Math.ceil(DELAY_END*FPS);
//         }
//     }else {
// //     Switch Players
//         playersTurn= !playersTurn;
//
//     }
//
//
// }



function Square(x, y, w, h){
    this.w=w;
    this.h=h;
    this.left= x;
    this.right= x+w;
    this.top= y;

    this.bot= y+h;

    this.highlight= null;
    this.numSelected= 0;
    this.owner= null;
    this.sideBot= {owner:null, selected:false}
    this.sideLeft= {owner:null, selected:false}
    this.sideRight= {owner:null, selected:false}
    this.sideTop= {owner:null, selected:false}


    this.contains= function (x, y){
        return x >= this.left && x< this.right  && y>=this.top && y< this.bot
    }
    this.drawFill = function(){
        if (this.owner == null){
            return;
        }

    //     light background
        ctx.fillStyle= getColor(this.owner, true);
        ctx.fillRect(
            this.left + STROKE, this.top + STROKE,
            this.w- STROKE*2, this.h- STROKE *2

        );

    // Owner text
        drawText(
            getText(this.owner, true),
            this.left+ this.w/2,
            this.top+ this.h/2,
            getColor(this.owner, false),
            TEXT_SIZE_CELL
        )
    }

    this.drawSide= function(side, color){
        switch(side){
            case Side.BOT:
                drawLine(this.left, this.bot, this.right, this.bot, color )
                break;
            case Side.LEFT:
                drawLine(this.left, this.top, this.left, this.bot, color )
                break;
            case Side.RIGHT:
                drawLine(this.right, this.top, this.right, this.bot, color )
                break;
            case Side.TOP:
                drawLine(this.left, this.top, this.right, this.top, color )
                break;
        }
    }

    this.drawSides= function(){

        // highlighting
        // if (this.highlight != null){
        //     this.drawSide(this.highlight, getColor(playersTurn, true))
        // }
    //      selected sides
        if (this.sideBot.selected){
            this.drawSide(Side.BOT, getColor(this.sideBot.owner, false));
        }
        if (this.sideLeft.selected){
            this.drawSide(Side.LEFT, getColor(this.sideLeft.owner, false));
        }
        if (this.sideRight.selected){
            this.drawSide(Side.RIGHT, getColor(this.sideRight.owner, false));
        }
        if (this.sideTop.selected){
            this.drawSide(Side.TOP, getColor(this.sideTop.owner, false));
        }

    }

    // this.highlightSide= function(x,y){
    //
    // //     Calculate the distances each side
    //     let dBot= this.bot- y;
    //     let dLeft= x-this.left;
    //     let dRight= this.right-x;
    //     let dTop= y- this.top;
    //
    // //     determine closest value
    //     let dClosest= Math.min(dBot, dLeft, dRight, dTop);
    //
    // //     highlight the closest if not already selected
    //     if(dClosest== dBot && !this.sideBot.selected){
    //         this.highlight= Side.BOT;
    //     }
    //     if(dClosest== dLeft && !this.sideLeft.selected){
    //         this.highlight= Side.LEFT;
    //     }
    //     if(dClosest== dRight && !this.sideRight.selected){
    //         this.highlight= Side.RIGHT;
    //     }
    //     if(dClosest== dTop && !this.sideTop.selected){
    //         this.highlight= Side.TOP;
    //     }
    //
    //
    // //     Return the highlighted side
    //     return this.highlight;
    // }
     this.selectSide=  function(side){
        // if(this.highlight == null){
        //     return;
        // }

    //     select the highlighted side

         switch (side){
             case Side.BOT:
                 this.sideBot.owner= playersTurn;
                 this.sideBot.selected= true;
                 break;
             case Side.LEFT:
                 this.sideLeft.owner= playersTurn;
                 this.sideLeft.selected= true;
                 break;
             case Side.RIGHT:
                 this.sideRight.owner= playersTurn;
                 this.sideRight.selected= true;
                 break;
             case Side.TOP:
                 this.sideTop.owner= playersTurn;
                 this.sideTop.selected= true;
                 break;
         }

        // this.highlight= null;

    //     increase the number of selected
         this.numSelected++;
         if(this.numSelected===4){
             this.owner= playersTurn;

         // //     increment score
         //     if (playersTurn){
         //         scorep1++;
         //     }else{
         //         scorep2++;
         //     }


         //     filled
             return true;
         }

    //      not filled
         return false;
    };

}

// Receive move via python message

// message format : {type:"move", t:"h"|"v", r:int, c:int, player:0|1, completed:bool}
//message format: {type:"reset"}
// message frmat: {type:"status", text: "..."}

window.addEventListener("message",function(ev){

    const data= ev.data;
    if (!data|| !data.type) return;

    if (data.type === "reset") {
        newGame();
        gameActive = true;
        document.getElementById('status-bar').textContent= "Game Started";
        return;
    }

    if (data.type==="status"){
        document.getElementById('status-bar').textContent= data.text;
        return;
    }

    if(data.type==="move"){
        const {t,r,c,player, completed}= data;
        const owner=player === 0;
        playersTurn= owner;

        // which side within each square does this line touch
        if(t==="h") {
            // horizontal line between row r and row r-1
            //bottom side of square(r-1,c) and top side of square(r,c)
            if (r > 0 && r - 1 < GRID_SIZE && c < GRID_SIZE) {
                squares[r - 1][c].selectSide(Side.BOT, owner);
            }

            if (r < GRID_SIZE && c < GRID_SIZE) {
                squares[r][c].selectSide(Side.TOP, owner);
            }
        }else{
                // Vertical line between col c and col c-1
                // right side of square (r,c-1) And left side of sqaure(r,c)
                if (c>0 && r< GRID_SIZE && c-1< GRID_SIZE){
                    squares[r][c-1].selectSide(Side.RIGHT, owner);
                }
                if( c<GRID_SIZE && r< GRID_SIZE){
                    squares[r][c].selectSide(Side.LEFT, owner);
                }
        }
        scorep1 = data.scorep1;
        scorep2= data.scorep2;
        playersTurn= data.next_turn===0;
    }
});

// Start loop
newGame();
setInterval(loop, 1000/FPS);