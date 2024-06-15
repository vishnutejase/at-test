import json, os
from datetime import datetime, timedelta
from pytz import timezone
from model import Session, Module, Log, User
from .generator_script import generatorScript

to_tz = timezone('UTC')  
script_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(script_dir, 'data')
futureSSID_path = os.path.join(data_dir, 'futureSSID.json')

def update_futureSSID(futureSSID):
    seed = 1000
    if len(futureSSID) > 2:
        seed = futureSSID[-1]
    while len(futureSSID) < 10000:
        futureSSID.append(generatorScript(seed))
        seed = futureSSID[-1]
    with open(futureSSID_path, "w") as file:
        json.dump(futureSSID, file)

def refreshSSID(module):
    session = Session()
    now = datetime.now().astimezone(to_tz)
    lastTime = module.lastRefreshTime.astimezone(to_tz)
    if module.isPaused is False and now - lastTime >= module.seedRefreshInterval:
        time = now - timedelta(minutes=5)
        recentLogsCount = session.query(Log).filter(Log.lastSeen >= time).count()

        module.lastRefreshTime = now.replace(second=0, microsecond=0)

        if recentLogsCount == 0:
            session.commit()
            return

        seed = module.seed
        newSeed = generatorScript(seed)
        module.SSID = 'amFOSS_' + str(newSeed)
        module.seed = newSeed
        with open(futureSSID_path, "r") as file:
            futureSSID = json.load(file)
        futureSSID = futureSSID[1:]
        update_futureSSID(futureSSID)
        session.commit()

def verify_ssid(ssid_list):
    with open(futureSSID_path, "r") as file:
        futureSSID = json.load(file)
    
    currentSSID = -1
    for sentSSID in ssid_list:
        try:
            if int(sentSSID.strip('amFOSS_')) in futureSSID:
                currentSSID = int(sentSSID.strip('amFOSS_'))
        except ValueError:
            pass
    if currentSSID != -1:
        return True
    return False
