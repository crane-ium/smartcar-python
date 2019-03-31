import smartcar
from flask import Flask, redirect, request, jsonify
from flask_cors import CORS
import json
import pickle

import os
import requests

app = Flask(__name__)
CORS(app)

_measurement_system = "imperial"
_debugflag = True
# global variable to save our access_token
try:
    access = pickle.load(open("bin/access_obj.p", "rb"))
    if _debugflag:
        print("Loaded pickle", flush=True)
except:
    access = None


# TODO: Authorization Step 1a: Launch Smartcar authorization dialog
client = smartcar.AuthClient(
    client_id=os.environ.get('CLIENT_ID'),
    client_secret=os.environ.get('CLIENT_SECRET'),
    redirect_uri=os.environ.get('REDIRECT_URI'),
    scope=['read_vehicle_info', 'read_odometer', 'read_location', 
           'control_security', 'read_vin'], #Authorize your vehicle through the account
    test_mode=True,
)

@app.route('/login', methods=['GET'])
def login():
    # if access:
    #     return redirect("localhost:8000/info")
    auth_url = client.get_auth_url()
    print('auth_url:', auth_url, flush=True)
    return redirect(auth_url)

# @app.route('/logout', methods=['GET'])
# def logout():
#     try:
#         os.remove("bin/access_obj.p")
#     except:
#         print("Failed logout attempt")
#     return redirect("localhost:8000/login")

@app.route('/exchange', methods=['GET'])
def exchange():
    code = request.args.get('code')
    print(code)

    global access
    access = client.exchange_code(code)
    with open("bin/access_obj.p", "wb") as obj:
        pickle.dump(access, obj)
    print(access, flush=True)
    for key, value in access.items():
        print(str(key)+' '+str(value),end='\n', flush=True)
    redirect("localhost:8000/info")
    return '', 200
    # return redirect("localhost:8000/info")

@app.route('/lock', methods=['GET'])
def lockcar():
    #Splash for locking car
    token = access['access_token']
    tempcar = smartcar.Vehicle(smartcar.get_vehicle_ids(token), token)
    string = lockchoosecar(tempcar)
    return jsonify(string)

@app.route('/unlock', methods=['GET'])
def unlockcar():
    #Splash for locking car
    token = access['access_token']
    tempcar = smartcar.Vehicle(smartcar.get_vehicle_ids(token), token)
    string = unlockchoosecar(tempcar)
    return jsonify(string)

def lockchoosecar(vehicle):
    if access == None:
        return "Not logged in"
    try:
        vehicle.lock()
        return ("Locked vehicle successfully")
    except:
        return ("Failed to lock")

def unlockchoosecar(vehicle):
    if access == None:
        return "Not logged in"
    try:
        vehicle.lock()
        return ("Unlocked vehicle successfully")
    except:
        return ("Failed to unlock")


@app.route('/vehicles', methods=['GET'])
def vehicles():
    #Call to define your vehicles
    token = access['access_token']
    headers = {'Authorization': f'Bearer {token}'}
    r = requests.get("https://api.smartcar.com/v1.0/vehicles", headers=headers)
    print(r.json(), flush=True)

    # return json.dumps(info)
    return jsonify(r.json())
    

@app.route('/info', methods=['GET'])
def info():
    #Display info for your vehicle collection
    #Request for info from api

    #Invalid url access
    if access == None:
        print("Not logged in", flush=True)
        return jsonify("Invalid URL: Not logged in")

    info = define_vehicles()
    
    return jsonify(info[1])

def define_vehicles():
    """
    Verify and instantiate the variables so we can store car info data

    @Returns: list of dictionaries containing car details
    """
    global access
    if access == None:
        error = 520
        errorstr = "Cannot access vehicle data: Not logged in"
        return jsonify({'error_code':error, 'errorstr':errorstr})
    vehicle_ids = smartcar.get_vehicle_ids(
        access['access_token'])['vehicles']
    print(vehicle_ids, flush=True)
    
    vehicle = list()
    for i, v_id in enumerate(vehicle_ids):
        vehicle.append(smartcar.Vehicle(v_id, access['access_token']))
        if _debugflag:
            print(vehicle[i])
    # vehicle = smartcar.Vehicle(vehicle_ids[0], access['access_token'])    # TODO: Request Step 4: Make a request to Smartcar API
    info = list()
    for i, _ in enumerate(vehicle):
        info.append(vehicle[i].info())
    for i, v in enumerate(vehicle):
        reading = get_odometer(v)
        if reading[0] > 0:
            info[i]['odometer'] = reading
        coordinates = get_location(v)
        if coordinates[0] <= 180 and coordinates[1] <= 180:
            info[i]['location'] = coordinates
    if _debugflag:
        print(info, flush=True)
    return vehicle, info

def get_location(vehicle):
    """
    Get latitude, longitude of the vehicle
    
    @Params: vehicle object
    @Returns: coordinates tuple
    """
    if access == None:
        return 181, 181
    
    v_id = vehicle.info()['id']
    url = f'https://api.smartcar.com/v1.0/vehicles/{v_id}/location'
    headers = {'Authorization': f'Bearer {access["access_token"]}', 'limit': '25'}
    r = requests.get(url, headers=headers)
    if _debugflag:
        print(r.json(), flush=True)
    if 'error' in r.json():
        return 181,181
    
    return r.json()['latitude'], r.json()['longitude']
    
def get_odometer(vehicle):
    """
    Returns odometer reading

    @Returns: (tuple) miles or kms of odometer, measurement system
    """
    if access == None:
        return (-1, _measurement_system)
    try:
        odometer = vehicle.odometer()['data']['distance']
    except:
        return -1, _measurement_system
    return odometer, _measurement_system
    # v_id = vehicle.info()['id']
    # token = access['access_token']
    # if _debugflag:
    #     print(access, flush=True)
    # url = f"https://api.smartcar.com/v1.0/vehicles/{v_id}/odometer"
    # headers = {'Authorization': f'Bearer {token}'}
    # if _debugflag:
    #     print(url, ", ", headers, flush=True)
    # req = requests.get(url, headers=headers)
    # if _debugflag:
    #     print(req.json(), flush=True)
    
    # #Check for errors
    # if 'error' in req.json():
    #     return (-1, f"error: {req.json()['error']} : {req.json()['message']}")

    # #No error -> return distance
    # return (req.json()['distance'], req.json()['SC-Unit-System'])

def verify():
    pass

def vehicle_to_string(vehicle):
    """
    Takes the vehicle object and neatly organizes it into
    user friendly readable string

    @Return: string
    """
    vstr = vehicle.info()['year'] + ' ' \
            + vehicle.info()['make'] + \
            + vehicle.info()['model'] + '\n'
    
    return vstr

if __name__ == '__main__':
    app.run(port=8000, debug=_debugflag)
