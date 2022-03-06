from glob import glob
import os
import time
from pypresence import Presence
from dotenv import load_dotenv

load_dotenv()

current_time = time.time()
state = ""
details = ""

client_id = os.getenv("DISCORD_CLIENTID")
RPC = Presence(client_id)
RPC.connect()

def update(newState, newDetails, running):
    global state
    global details 
    global current_time

    if newState != state or newDetails != details:
        current_time = time.time()
        state = newState
        details = newDetails
        
    upd = RPC.update(state = newState, details = newDetails, start = current_time)
