"""Handles Discord integration"""
import os
import time
import logging
from pypresence import Presence
from pypresence import DiscordError
from dotenv import load_dotenv

load_dotenv()
client_id = os.getenv("DISCORD_CLIENTID")

class Discord:
    """Manages Discord status"""
    def __init__(self):
        self.logger = logging.getLogger("Discord")
        self.current_time = time.time()
        self.state = ""
        self.details = ""
        try:
            if client_id is None:
                raise ValueError()
            self.RPC = Presence(client_id)
            self.RPC.connect()
            self.failed = False
        except DiscordError:
            self.failed = True
            self.logger.warning("Failed to connect")
        except ValueError:
            self.failed = True 
            self.logger.warning("No ClientID provided")


    def update(self, newState, newDetails):
        """Updates Discord status"""
        if not self.failed:
            if newState != self.state or newDetails != self.details:
                self.current_time = time.time()
                self.state = newState
                self.details = newDetails
                self.logger.info("Status updated")
            self.RPC.update(state = newState, details = newDetails, start = self.current_time)

    def clear(self):
        """Clears presence"""
        if not self.failed:
            self.RPC.clear()
            self.RPC.close()
