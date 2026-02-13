class CarState:
    def __init__(self):
        self.ac_on = False
        self.ac_temp = 22
        self.destination = None
        self.lights_on = False
        self.wipers_on = False
        self.speed = 0          # simulated
        self.fuel = 85          # %

        self.windows = {"driver": 0, "passenger": 0} # 0=closed, 100=open
        self.ai_talking = False
        self.is_listening = False
