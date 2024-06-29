import os
import socketio
from decouple import config

sio = socketio.Server(cors_allowed_origins=config('ALLOWED_HOSTS'))
app = socketio.WSGIApp(sio)
sid_to_game_clients = {}
sid_to_game_ids = {}
all_game_rooms = {}
all_game_clients = {}
DEBUG = False

class GameClient():
    def __init__(self, _username, _socketId, _ready):
        self.username = _username
        self.socketId = _socketId
        self.ready = _ready

    def get_username(self):
        return self.username
    
    def get_socketId(self):
        return self.socketId
    
    def get_ready(self):
        return self.ready
    
    def set_ready(self, status):
        self.ready = status

class GameRoom():
    def __init__(self, _player1, _player2, _gameId):
        self.player1 = _player1
        self.player2 = _player2
        self.gameId = _gameId

    def set_player1(self, _player1):
        self.player1 = _player1

    def set_player2(self, _player2):
        self.player2 = _player2

    def get_player1(self):
        return self.player1

    def get_player2(self):
        return self.player2

    def send_tap(x, y, _to):
        data = x + "|" + y
        print(f"Sending tap to {_to}")
        sio.emit("TAP", data, room=_to)
        # _io.to(_to).emit('TAP', data)

@sio.event
def connect(sid, environ):
    print('Client connected', sid)

@sio.event
def game_id(sid, data):
    data_split = data.split("|")
    print(data_split)
    c_gameId = data_split[0]
    c_username = data_split[1]
    place = data_split[2]
    new_client = None
    new_game_room = None
    completed_game_room = False
    key = c_gameId + "|" + place
    print(f"CUSERNAME: {c_username}")
    new_client = GameClient(c_username, sid, False)
    print(new_client.get_username())
    all_game_clients[key] = new_client
    sid_to_game_clients[sid] = new_client
    sid_to_game_ids[sid] = c_gameId

    if place == "1":
        try:
            new_game_room = all_game_rooms[c_gameId]
            new_game_room.set_player1(new_client)
            completed_game_room = True
            print("GOT THROUGH THE TRY BLOCK OF GETTING A GAME")
        except:
            new_game_room = GameRoom(new_client, None, c_gameId)
            all_game_rooms[c_gameId] =  new_game_room
            sio.emit("GAMEID", "NOTYET", room=sid)
            print("GOT THROUGH EXCEPT BLOCK OF MAKING A GAME")
    elif place == "2":
        try:
            new_game_room = all_game_rooms[c_gameId]
            new_game_room.set_player2(new_client)
            completed_game_room = True
            print("GOT THROUGH THE TRY BLOCK OF GETTING A GAME PLAYER 2")
        except:
            new_game_room = GameRoom(None, new_client, c_gameId)
            all_game_rooms[c_gameId] =  new_game_room
            sio.emit("GAMEID", "NOTYET", room=sid)
            print("GOT THROUGH THE TRY BLOCK OF MAKING A GAME PLAYER 2")
    if completed_game_room:
        print("COMPLETED THE GAME ROOM")
        print(new_game_room)
        sio.emit('GAMEID', "SUCCESS", room=new_game_room.get_player1().get_socketId())
        sio.emit('GAMEID', "SUCCESS", room=new_game_room.get_player2().get_socketId())

@sio.event
def ready(sid, data):
    print("IN READY HANDLER")
    data_split = data.split("|")
    print(f"DATA SPLIT: {data_split}")
    username = data_split[0]
    print(f"USERNAME: {username}")
    game_Id = data_split[1]
    print(f"GAMEID: {game_Id}")
    user = all_game_clients[game_Id + "|1"]
    print(f"USER: {user.get_username()}")
    user2 = all_game_clients[game_Id + "|2"]
    print(f"USER2: {user2.get_username()}")

    if user.get_username() == username:
        print("IT IS USER 1")
        user.set_ready(True)
        message = str(user.get_ready()) + "|" + str(user2.get_ready()) + "|" + username
        print(f"MESSAGE: {message}")
        sio.emit("READY", message, room=user2.get_socketId())
        # io.to(user2.get_socketId()).emit('READY', message)
    elif user2.get_username() == username:
        print("IT IS USER 2")
        user2.set_ready(True)
        message = str(user2.get_ready()) + "|" + str(user.get_ready()) + "|" + username
        print(f"MESSAGE: {message}")
        sio.emit("READY", message, room=user.get_socketId())
        # io.to(user.get_socketId()).emit('READY', message)

@sio.event
def start_game(sid, game_id):
    user1 = all_game_clients[game_id + "|1"]
    user2 = all_game_clients[game_id + "|2"]
    sio.emit("STARTCGAME", room=user1.get_socketId())
    sio.emit("STARTCGAME", room=user2.get_socketId())
    # io.to(user1.get_socketId()).emit('STARTCGAME');
    # io.to(user2.get_socketId()).emit('STARTCGAME');

@sio.event
def tap(sid, index):
    index_split1 = index.split("|")
    index_split2 = index_split1[1].split("*")
    x_index = index_split1[0]
    y_index = index_split2[0]
    game_id = index_split2[1]
    user1 = all_game_clients[game_id + "|1"]
    user2 = all_game_clients[game_id + "|2"]
    reciever = None
    curr_game = all_game_rooms[game_id]
    if (user1.get_socketId() == sid):
        reciever = user2
    elif (user2.get_socketId() == sid):
        reciever = user1
    data = x_index + "|" + y_index
    print(f"Sending tap to {reciever.get_socketId()}")
    sio.emit("TAP", data, room=reciever.get_socketId())
    # curr_game.send_tap(x_index, y_index, reciever.get_socketId())

@sio.event
def remove_game_client(sid, values):
    values_split = values.split("|")
    value = values_split[0]
    game_id = values_split[1]
    removed_user = get_user(game_id, sid)
    removed_user_position = get_map_position(game_id, sid)
    if (value == "EXIT"):
        del all_game_clients[removed_user_position]
        try:
            if (removed_user_position.split("|")[1] == "1"):
                user = all_game_clients[removed_user_position.split("|")[0] + "|2"]
                sio.emit("DISCONNECT", room=user.get_socketId())
                # io.to(user2.get_socketId()).emit("DISCONNECT")
            elif (removed_user_position.split("|")[1] == "2"):
                user = all_game_clients[removed_user_position.split("|")[0] + "|1"]
                sio.emit("DISCONNECT", room=user.get_socketId())
                # io.to(user.get_socketId()).emit("DISCONNECT")
        except:
            print("ERROR EMITING TO OTHER CLIENT")
    else:
        del all_game_clients[removed_user_position]
        del sid_to_game_clients[sid]
        del sid_to_game_ids[sid]
    if (removed_user != None):
        sio.emit("REMOVEDUSER", value, room=removed_user.get_socketId())
        # io.to(removed_user.get_socketId()).emit("REMOVEDUSER", value);

@sio.event
def cancelled(sid, data):
    data_split = data.split("|")
    canceled_username = data_split[0]
    game_id = data_split[1]
    user1 = all_game_clients[game_id + "|1"]
    user2 = all_game_clients[game_id + "|2"]
    if (user1.get_username() == canceled_username):
        try:
            sio.emit("CANCELLED", canceled_username, room=user2.get_socketId())
            # io.to(user2.get_socketId()).emit('CANCELLED', canceled_username)
        except:
            print("IN THE CANCELLED CATCH BLOCK 1")
    elif (user2.get_username() == canceled_username):
        try:
            sio.emit("CANCELLED", canceled_username, room=user1.get_socketId())
            # io.to(user1.get_socketId()).emit('CANCELLED', canceled_username)
        except:
            print("IN THE CANCELLED CATCH BLOCK 2")

@sio.event
def declined(sid, gameId):
    user = None
    try:
        user = all_game_clients[gameId + "|1"]
        sio.emit("DECLINED", room=user.get_socketId())
        # io.to(user.get_socketId()).emit('DECLINED')
    except:
        try:
            user = all_game_clients[gameId + "|2"]
            sio.emit("DECLINED", room=user.get_socketId())
            # io.to(user.get_socketId()).emit('DECLINED')
        except:
            print("CLIENT ALREADY LEFT")

@sio.event
def play_again(sid, data):
    data_split = data.split("|")
    username = data_split[0]
    game_id = data_split[1]
    user1 = get_user(game_id, sid)
    user1_pos = get_map_position(game_id, sid)
    user2 = None
    if (user1_pos.split("|")[1] == "1"):
        user2 = all_game_clients[game_id + "|2"]
    else:
        user2 = all_game_clients[game_id + "|1"]
    sio.emit("PLAYAGAIN", username, room=user1.get_socketId())
    sio.emit("PLAYAGAIN", username, room=user2.get_socketId())
    # io.to(user1.get_socketId()).emit('PLAYAGAIN', username)
    # io.to(user2.get_socketId()).emit('PLAYAGAIN', username)

@sio.event
def opponent_left(sid, data):
    try:
        data_split = data.split("|")
        username = data_split[0]
        game_id = data_split[1]
        user1 = get_map_position(game_id, sid)
        user2 = None
        if (user1.split("|")[1] == "1"):
            user2 = all_game_clients[game_id + "|2"]
        else:
            user2 = all_game_clients[game_id + "|1"]
        if (user2 != None):
            sio.emit("OPPLEFT", username, room=user2.get_socketId())
            # io.to(user2.get_socketId()).emit('OPPLEFT', username)
    except:
        print("Opponent already left.")

@sio.event
def disconnect(sid):
    print("IN DISCONNECT HANDLER")
    try:
        curr_gameId = sid_to_game_ids[sid]
        player1_key = curr_gameId + "|1"
        player2_key = curr_gameId + "|2"
        player1 = all_game_clients[player1_key]
        player2 = all_game_clients[player2_key]
        if (player1):
            del all_game_clients[player1_key]
            del sid_to_game_clients[player1.get_socketId()]
            del sid_to_game_ids[player1.get_socketId()]
        if (player2):
            del all_game_clients[player2_key]
            del sid_to_game_clients[player2.get_socketId()]
            del sid_to_game_ids[player2.get_socketId()]
    except:
        print("CLIENT ALREADY LEFT")

@sio.event
def message(sid, data):
    print('Message from client:', data)


def get_user(game_id, socket_id):
    try:
        user = all_game_clients[game_id + "|1"]
        if (user.get_socketId() == socket_id):
            return user
        else:
            user = all_game_clients.get[game_id + "|2"]
            if (user.get_socketId() == socket_id):
                return user
            else:
                print("USER NOT IN CLIENTS")
                return None
    except:
        user = all_game_clients[game_id + "|2"]
        if (user.get_socketId() == socket_id):
            return user
        else:
            print("USER NOT IN CLIENTS")
            return None

def get_map_position(game_id, socket_id):
    try:
        user = all_game_clients[game_id + "|1"]
        if (user.get_socketId() == socket_id):
            return game_id + "|1"
        else:
            user = all_game_clients[game_id + "|2"]
            if (user.get_socketId() == socket_id):
                return game_id + "|2"
            else:
                print("USER NOT IN CLIENTS")
                return None
    except:
        user = all_game_clients[game_id + "|2"]
        if (user.get_socketId() == socket_id):
            return game_id + "|2"
        else:
            print("USER NOT IN CLIENTS")
            return None

if __name__ == '__main__':
    import eventlet
    if DEBUG:
        eventlet.wsgi.server(eventlet.listen(('localhost', 8763)), app)
    else:
        eventlet.wsgi.server(eventlet.listen(('0.0.0.0', int(os.getenv('PORT', 8765)))), app)


#             socket.on('PLAYAGAIN', (data) => {
#                 var data_split = data.split("|");
#                 var username = data_split[0];
#                 var game_id = data_split[1];
#                 var user1 = get_user(game_id, socket.id);
#                 var user1_pos = get_map_position(game_id, socket.id);
#                 var user2 = null;
#                 if (user1_pos.split("|")[1] == "1") {
#                     user2 = game_clients.get(game_id + "|2");
#                 }
#                 else {
#                     user2 = game_clients.get(game_id + "|1");
#                 }
#                 io.to(user1.get_socketId()).emit('PLAYAGAIN', username);
#                 io.to(user2.get_socketId()).emit('PLAYAGAIN', username);
#             })


#             socket.on('OPPLEFT', (data) => {
#                 var data_split = data.split("|");
#                 var username = data_split[0];
#                 var game_id = data_split[1];
#                 var user1 = get_map_position(game_id, socket.id);
#                 var user2 = null;
#                 if (user1.split("|")[1] == "1") {
#                     user2 = game_clients.get(game_id + "|2");
#                 }
#                 else {
#                     user2 = game_clients.get(game_id + "|1");
#                 }
#                 if (user2 != null) {
#                     io.to(user2.get_socketId()).emit('OPPLEFT', username);
#                 }
#             })