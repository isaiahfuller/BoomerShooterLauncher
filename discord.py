import os
import time
import logging
from pypresence import Presence
from dotenv import load_dotenv

load_dotenv()
client_id = os.getenv("DISCORD_CLIENTID")

class Discord:
    def __init__(self):
        self.current_time = time.time()
        self.state = ""
        self.details = ""
        try:
            self.RPC = Presence(client_id)
            self.RPC.connect()
            self.failed = False
        except:
            self.failed = True
            logging.warning("[Discord] Failed to connect")


    def update(self, newState, newDetails, running):
        if not self.failed:
            if newState != self.state or newDetails != self.details:
                self.current_time = time.time()
                self.state = newState
                self.details = newDetails
                
            upd = self.RPC.update(state = newState, details = newDetails, start = self.current_time)
