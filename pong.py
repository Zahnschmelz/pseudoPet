import asyncio
import json
import socket
import threading
import random
import time
import math
from os import environ
import pygame

try:
    import websockets
    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False
    print("[pong] WARNUNG: 'websockets' nicht installiert (pip install websockets)")

PONG_DEBUG = False

def dbg(*args):
    if PONG_DEBUG:
        print("[pong %s]" % time.strftime("%H:%M:%S"), *args, flush=True)

def _ws_closed(ws):
    if ws is None:
        return True
    if getattr(ws, "closed", None) is True:
        return True
    if "CLOSED" in str(getattr(ws, "state", "")).upper():
        return True
    return False

if HAS_WEBSOCKETS:
    dbg("websockets Version:", getattr(websockets, "__version__", "?"))

PONG_PORT = 9876
PONG_WIN_SCORE = 3
PONG_FPS = 24
PONG_LAN_NO_COOLDOWN = True
MSG_HELLO = "hello"
MSG_WELCOME = "welcome"
MSG_STATE = "state"
MSG_INPUT = "input"
MSG_READY = "ready"
MSG_START = "start"
MSG_PAUSE = "pause"
MSG_RESUME = "resume"
MSG_RESTART = "restart"
MSG_RESTART_REQ = "restart_req"
MSG_PAUSE_REQ = "pause_req"
MSG_RESUME_REQ = "resume_req"
MSG_QUIT = "quit"
MSG_PING = "ping"
MSG_PONG = "pong"
WHITE = (238, 230, 220)

# ======================
# NETZWERK-UTILITIES
# ======================
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"

def get_subnet_ips(local_ip):
    parts = local_ip.split(".")
    if len(parts) != 4:
        return ["127.0.0.1"]
    base = ".".join(parts[:3])
    return ["127.0.0.1"] + [f"{base}.{i}" for i in range(1, 255)
                            if f"{base}.{i}" != local_ip]

# =================
# WEBSOCKET SERVER
# =================
class PongServer:
    def __init__(self):
        self.running = False
        self.client_ws = None
        self.client_connected = threading.Event()
        self.client_dir = 0
        self.client_pet_key = None
        self.pause_req = False
        self.resume_req = False
        self.restart_req = False
        self.loop = None
        self._thread = None
        self._server = None

    def start(self):
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def _run_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._serve())

    async def _serve(self):
        self.running = True
        try:
            self._server = await websockets.serve(
                self._handle_client, "0.0.0.0", PONG_PORT)
            dbg("SERVER LAUSCHT auf 0.0.0.0:%d (lokale IP: %s)"
                % (PONG_PORT, get_local_ip()))
            while self.running:
                await asyncio.sleep(0.1)
        except OSError as e:
            dbg("SERVER FEHLER (Port belegt?):", e)
        except Exception:
            import traceback
            dbg("SERVER CRASH:")
            traceback.print_exc()
        finally:
            if self._server:
                self._server.close()

    async def _handle_client(self, websocket, path=None):
        dbg("SERVER: neuer TCP/WS-Kontakt:",
            getattr(websocket, "remote_address", "?"))
        if self.client_ws is not None and not _ws_closed(self.client_ws):
            dbg("SERVER: Raum voll -> weise ab")
            await websocket.send(json.dumps({"type": "full"}))
            await websocket.close()
            return
        self.client_ws = websocket
        self.client_connected.set()
        dbg("SERVER: Client verbunden (Handshake OK)")
        try:
            await websocket.send(json.dumps(
                {"type": MSG_WELCOME, "player": 2,
                 "win_score": PONG_WIN_SCORE}))
            async for message in websocket:
                data = json.loads(message)
                t = data.get("type")
                if t != MSG_STATE:
                    dbg("SERVER RX:", t, data.get("dir", ""))
                if t == MSG_INPUT:
                    self.client_dir = data.get("dir", 0)
                elif t == "pet":
                    self.client_pet_key = data.get("key")
                elif t == MSG_PAUSE_REQ:
                    self.pause_req = True
                elif t == MSG_RESUME_REQ:
                    self.resume_req = True
                elif t == MSG_RESTART_REQ:
                    self.restart_req = True
                elif t == MSG_PING:
                    await websocket.send(json.dumps({"type": MSG_PONG}))
                elif t == MSG_QUIT:
                    break
        except Exception as e:
            dbg("SERVER: Client-Fehler:", repr(e))
        finally:
            self.client_ws = None
            self.client_connected.clear()
            self.client_dir = 0
            dbg("SERVER: Client getrennt / Raum wieder frei")

    async def _send(self, msg_dict):
        if self.client_ws:
            try:
                await self.client_ws.send(json.dumps(msg_dict))
            except Exception:
                pass

    def send_msg(self, msg_dict):
        if self.client_ws and self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self._send(msg_dict), self.loop)

    def send_state(self, state_dict):
        self.send_msg(state_dict)

    def get_client_dir(self):
        return self.client_dir

    def consume_pause_req(self):
        v = self.pause_req; self.pause_req = False; return v

    def consume_resume_req(self):
        v = self.resume_req; self.resume_req = False; return v

    def consume_restart_req(self):
        v = self.restart_req; self.restart_req = False; return v

    def stop(self):
        self.running = False
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        if self._thread:
            self._thread.join(timeout=2.0)


# ================
# WEBSOCKET
# ================
class PongClient:
    def __init__(self):
        self.running = False
        self.connected = threading.Event()
        self.ws = None
        self.loop = None
        self._thread = None
        self.host_ip = None
        self.game_state = None
        self.server_msg = None
        self._lock = threading.Lock()

    def _port_open(self, ip, timeout=0.25):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            ok = (s.connect_ex((ip, PONG_PORT)) == 0)
            s.close()
            return (ip, ok)
        except Exception:
            return (ip, False)

    def scan_and_connect(self, timeout=10.0):
        local_ip = get_local_ip()
        subnet = get_subnet_ips(local_ip)
        dbg("CLIENT: lokale IP", local_ip, "| scanne", len(subnet),
            "IPs PARALLEL auf Port", PONG_PORT)
        open_ips = []
        try:
            from concurrent.futures import ThreadPoolExecutor, as_completed
            with ThreadPoolExecutor(max_workers=48) as ex:
                futs = [ex.submit(self._port_open, ip) for ip in subnet]
                for fut in as_completed(futs):
                    ip, ok = fut.result()
                    if ok:
                        open_ips.append(ip)
        except Exception as e:
            dbg("CLIENT: Scan-Fehler:", repr(e))
        open_ips.sort(key=lambda ip: int(ip.rsplit(".", 1)[-1]))
        dbg("CLIENT: offene Ports gefunden:", open_ips or "KEINE")
        if not open_ips:
            dbg("CLIENT: kein Raum im Subnetz", local_ip + ".x")
            return False
        for ip in open_ips:
            self.host_ip = ip
            dbg("CLIENT: versuche WS-Connect zu", ip)
            self._thread = threading.Thread(target=self._run_loop,
                                            daemon=True)
            self._thread.start()
            if self.connected.wait(timeout=5.0):
                dbg("CLIENT: VERBUNDEN mit", ip)
                return True
            dbg("CLIENT: Connect zu", ip, "fehlgeschlagen -> naechste IP")
            if self._thread:
                self._thread.join(timeout=2.0)
            self.connected.clear()
        return False

    def _run_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._connect())

    async def _connect(self):
        self.running = True
        try:
            dbg("CLIENT: websockets.connect ->",
                f"ws://{self.host_ip}:{PONG_PORT}")
            async with websockets.connect(f"ws://{self.host_ip}:{PONG_PORT}") as ws:
                self.ws = ws
                dbg("CLIENT: TCP+WS-Handshake OK, sende HELLO")
                await ws.send(json.dumps({"type": MSG_HELLO, "name": "Player2"}))
                resp = await asyncio.wait_for(ws.recv(), timeout=5.0)
                data = json.loads(resp)
                dbg("CLIENT: erste Server-Message:", data.get("type"))
                if data.get("type") == MSG_WELCOME:
                    self.connected.set()
                    dbg("CLIENT: WELCOME erhalten -> verbunden als Spieler 2")
                    while self.running:
                        try:
                            msg = await asyncio.wait_for(ws.recv(), timeout=0.5)
                            parsed = json.loads(msg)
                            with self._lock:
                                if parsed.get("type") == MSG_STATE:
                                    self.game_state = parsed
                                else:
                                    self.server_msg = parsed
                        except asyncio.TimeoutError:
                            continue
                        except Exception:
                            break
                elif data.get("type") == "full":
                    dbg("CLIENT: Raum ist voll!")
        except Exception as e:
            import traceback
            dbg("CLIENT: Verbindungsfehler:", repr(e))
            traceback.print_exc()
        finally:
            self.connected.clear()
            self.running = False
            dbg("CLIENT: Empfangs-Loop beendet")

    async def _send(self, data):
        try:
            await self.ws.send(json.dumps(data))
        except Exception:
            pass

    def send_input(self, direction):
        if self.ws and self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._send({"type": MSG_INPUT, "dir": direction}), self.loop)

    def send_msg(self, msg_dict):
        if self.ws and self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self._send(msg_dict), self.loop)

    def get_state(self):
        with self._lock:
            return self.game_state

    def get_server_msg(self):
        with self._lock:
            msg = self.server_msg
            self.server_msg = None
            return msg

    def stop(self):
        self.running = False
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        if self._thread:
            self._thread.join(timeout=2.0)


# ====================
# AI-GEGNER
# ====================
class PongAI:
    def __init__(self, difficulty=0.42):
        self.difficulty = difficulty
        self.reaction_timer = 0.0
        self.target_dir = 0
        self.pred_error = 0.0
        self.last_ball_vy = 0

        self.reaction_timer = 0.7 + (1.0 - self.difficulty) * 0.7

    def update(self, ball_x, ball_y, ball_vx, ball_vy, paddle_x, dt):
        self.reaction_timer -= dt
        if self.reaction_timer > 0:
            return self.target_dir
        self.reaction_timer = (1.0 - self.difficulty) * 0.3
        if ball_vy * self.last_ball_vy < 0:
            self.pred_error = random.uniform(-1, 1) * (1.0 - self.difficulty) * 30
        self.last_ball_vy = ball_vy

        if ball_vy < 0:
            t_reach = abs(ball_y) / max(abs(ball_vy), 1)
            pred_x = ball_x + ball_vx * t_reach
            pred_x += self.pred_error
            diff = pred_x - paddle_x

            deadzone = 30
            self.target_dir = 0 if abs(diff) < deadzone else (-1 if diff < 0 else 1)
        else:
            diff = 120 - paddle_x
            deadzone = 30
            self.target_dir = 0 if abs(diff) < deadzone else (-1 if diff < 0 else 1)

        return self.target_dir


# ====================
# SPIELLOGIK
# ====================
class PongGame:
    FIELD_W = 240
    FIELD_H = 230
    PADDLE_W = 44
    PADDLE_H = 6
    PADDLE_Y_TOP = 12
    PADDLE_Y_BOT = FIELD_H - 18
    BALL_SIZE = 6
    PADDLE_SPEED = 165
    BALL_SPEED_INIT = 70
    BALL_SPEED_MAX = 200
    BALL_ACCEL = 3.5

    def __init__(self):
        self.score_p1 = 0
        self.score_p2 = 0
        self.winner = 0
        self.state = "ready"
        self.score_flash_t = 0.0
        self.score_to_win = PONG_WIN_SCORE
        self.reset()

    def reset(self):
        self.p1_x = self.FIELD_W / 2
        self.p2_x = self.FIELD_W / 2
        self.ball_x = self.FIELD_W / 2
        self.ball_y = self.FIELD_H / 2
        angle = random.uniform(0.3, 1.2)
        self.ball_vx = math.cos(angle) * self.BALL_SPEED_INIT * random.choice([-1, 1])
        self.ball_vy = math.sin(angle) * self.BALL_SPEED_INIT * random.choice([-1, 1])
        self.ball_speed = self.BALL_SPEED_INIT

    def reset_match(self):
        self.score_p1 = 0
        self.score_p2 = 0
        self.winner = 0
        self.state = "ready"
        self.reset()

    def start(self):
        self.state = "playing"
        self.reset()

    def _bounce(self, paddle_x, top):
        offset = (self.ball_x - paddle_x) / (self.PADDLE_W / 2)
        offset = max(-1.0, min(1.0, offset))
        self.ball_vx = offset * self.ball_speed * 0.7
        self.ball_speed = min(self.BALL_SPEED_MAX, self.ball_speed + self.BALL_ACCEL)
        mag = math.hypot(self.ball_vx, self.ball_vy) or 1.0
        self.ball_vx = self.ball_vx / mag * self.ball_speed
        self.ball_vy = (abs(self.ball_vy) / mag * self.ball_speed) * (-1 if top is False else 1)
        if top:
            self.ball_vy = abs(self.ball_vy)
        else:
            self.ball_vy = -abs(self.ball_vy)

    def update(self, dt, p1_dir, p2_dir):
        if self.state == "scored":
            self.score_flash_t -= dt
            if self.score_flash_t <= 0:
                self.reset()
                self.state = "playing"
            return
        if self.state != "playing":
            return

        half = self.PADDLE_W / 2
        self.p1_x = max(half, min(self.FIELD_W - half, self.p1_x + p1_dir * self.PADDLE_SPEED * dt))
        self.p2_x = max(half, min(self.FIELD_W - half, self.p2_x + p2_dir * self.PADDLE_SPEED * dt))

        self.ball_x += self.ball_vx * dt
        self.ball_y += self.ball_vy * dt
        r = self.BALL_SIZE / 2

        if self.ball_x <= r:
            self.ball_x = r
            self.ball_vx = abs(self.ball_vx)
        elif self.ball_x >= self.FIELD_W - r:
            self.ball_x = self.FIELD_W - r
            self.ball_vx = -abs(self.ball_vx)

        if (self.ball_vy < 0
                and self.ball_y - r <= self.PADDLE_Y_TOP + self.PADDLE_H
                and self.ball_y - r >= self.PADDLE_Y_TOP - 4
                and abs(self.ball_x - self.p2_x) <= half + r):
            self.ball_y = self.PADDLE_Y_TOP + self.PADDLE_H + r
            self._bounce(self.p2_x, top=True)

        if (self.ball_vy > 0
                and self.ball_y + r >= self.PADDLE_Y_BOT
                and self.ball_y + r <= self.PADDLE_Y_BOT + self.PADDLE_H + 4
                and abs(self.ball_x - self.p1_x) <= half + r):
            self.ball_y = self.PADDLE_Y_BOT - r
            self._bounce(self.p1_x, top=False)

        if self.ball_y < -self.BALL_SIZE:
            self.score_p1 += 1
            self._point(1)
        elif self.ball_y > self.FIELD_H + self.BALL_SIZE:
            self.score_p2 += 1
            self._point(2)

    def _point(self, scorer):
        if scorer == 1 and self.score_p1 >= self.score_to_win:
            self.state = "gameover"; self.winner = 1
        elif scorer == 2 and self.score_p2 >= self.score_to_win:
            self.state = "gameover"; self.winner = 2
        else:
            self.state = "scored"; self.score_flash_t = 1.0

    def get_state_dict(self):
        return {"type": MSG_STATE,
                "p1_x": self.p1_x, "p2_x": self.p2_x,
                "ball_x": self.ball_x, "ball_y": self.ball_y,
                "score_p1": self.score_p1, "score_p2": self.score_p2,
                "state": self.state, "winner": self.winner}

# ==================
# MINIGAME
# ==================
class MiniGamePong:
    FIELD_OY = 30

    def __init__(self, pet, mode="ai"):
        self.pet = pet
        self.mode = mode
        self.finished = False
        self.blocked_reason = None
        self.phase = "lobby"

        if getattr(pet, "sleeping", False):
            self.blocked_reason = "sleep"
        elif mode in ("host", "client") and PONG_LAN_NO_COOLDOWN:
            pass
        elif pet.age - getattr(pet, "_last_minigame", -1e9) < 100.0:
            self.blocked_reason = "cooldown"
        if self.blocked_reason:
            self.finished = True
            self.phase = "blocked"
            return

        self.game = PongGame()
        self.ai = PongAI() if mode == "ai" else None
        self._init_mascots()
        self._pet_send_t = 0.0
        self.server = None
        self.client = None
        self.network_ready = False
        self.input_dir = 0
        self.lobby_msg = ""
        self.lobby_timer = 0.0
        self.scan_result = None
        self.winner_text = ""
        self.gameover_sel = 0
        self.pause_sel = 0
        self.pulse_dir = 0
        self._last_sent_dir = 0
        self._game = None
        self._btn_cd = {}
        self._old_repeat = pygame.key.get_repeat()
        pygame.key.set_repeat(150, 50)
        self.frame_acc = 0.0
        self.frame_interval = 1.0 / PONG_FPS
        self.play_time = 0.0
        self._applied_pet_bonus = False

        if mode == "host":
            if not HAS_WEBSOCKETS:
                self.lobby_msg = "WEBSOCKETS MISSING!\npip install websockets"
                self.phase = "error"
                return
            self.server = PongServer()
            self.server.start()
            self.lobby_msg = "WAITING..."
        elif mode == "client":
            if not HAS_WEBSOCKETS:
                self.lobby_msg = "WEBSOCKETS MISSING!\npip install websockets"
                self.phase = "error"
                return
            self.client = PongClient()
            threading.Thread(
                target=lambda: setattr(self, "scan_result",
                                       self.client.scan_and_connect(8.0)),
                daemon=True).start()
        else:
            self.phase = "ready"

    # ---------------- MASCOTS ----------------
    MASCOT_SPEED = 70.0

    def _init_mascots(self):
        self.mascot = {
            "host_key": (self.pet.get_sprite_key()
                         if self.mode in ("ai", "host") else None),
            "guest_key": (self.pet.get_sprite_key() if self.mode == "client"
                          else self._random_pet_key()),
            "host_x": 212.0,
            "guest_x": 26.0,
            "host_corner": "right",
            "guest_corner": "left",
            "host_hit_cd": 0.0,
            "guest_hit_cd": 0.0,
        }

    @staticmethod
    def _mascot_row_y(role):
        if role == "guest":
            return PongGame.PADDLE_Y_TOP   # 12
        else:
            return PongGame.PADDLE_Y_BOT   # 212

    @staticmethod
    def _corner_x(corner):
        return 26.0 if corner == "left" else 212.0

    def _random_pet_key(self):
        import sys
        m = sys.modules.get("main") or sys.modules.get("__main__")
        br = getattr(m, "EVOLUTION_BRANCHES", None) if m else None
        if not br:
            return None
        key = random.choice(list(br.keys()))
        stages = [s for s in ("baby", "child", "teen", "adult")
                  if s in br[key]]
        return br[key][random.choice(stages)] if stages else None

    def _sprite_surf(self, key, scale, color):
        import sys
        m = sys.modules.get("main") or sys.modules.get("__main__")
        fn = getattr(m, "make_sprite_surface", None) if m else None
        if fn is None:
            return None
        try:
            return fn(key, scale, color)
        except Exception:
            return None

    def _mascot_hit_check(self, dt):
        m = self.mascot
        bx, by = self.game.ball_x, self.game.ball_y
        for role in ("host", "guest"):
            m[role + "_hit_cd"] = max(0.0, m[role + "_hit_cd"] - dt)

            tx = self._corner_x(m[role + "_corner"])
            dx = tx - m[role + "_x"]
            if abs(dx) > 0.5:
                step = self.MASCOT_SPEED * dt
                if abs(dx) <= step:
                    m[role + "_x"] = tx
                else:
                    m[role + "_x"] += step if dx > 0 else -step
                    if abs(tx - m[role + "_x"]) < 0.5:
                        m[role + "_x"] = tx

            if m[role + "_hit_cd"] <= 0:
                cy = self._mascot_row_y(role)
                if (abs(bx - m[role + "_x"]) < 14
                        and abs(by - cy) < 14):
                    m[role + "_corner"] = "left" if m[role + "_corner"] == "right" else "right"
                    m[role + "_hit_cd"] = 0.8

    def _draw_mascots(self, game):
        S = self._S(game)
        m = self.mascot
        if self.mode in ("ai", "host"):
            own_key, opp_key = m.get("host_key"), m.get("guest_key")
            own_x, opp_x = m["host_x"], m["guest_x"]
        else:
            own_key, opp_key = m.get("guest_key"), m.get("host_key")
            own_x, opp_x = m["guest_x"], m["host_x"]

        own_y = self._mascot_row_y("host") + self.FIELD_OY
        opp_y = self._mascot_row_y("guest") + self.FIELD_OY

        bob = abs(math.sin(time.time() * 4.0)) * 2 * S
        for key, mx, my in ((own_key, own_x, own_y), (opp_key, opp_x, opp_y)):
            if not key:
                continue
            surf = self._sprite_surf(key, 2 * S, self._palette(game)[0])
            if not surf:
                continue
            game.surface.blit(surf, surf.get_rect(
                center=(int(mx * S), int(my * S - bob))))

    # ---------------- UPDATE ----------------
    def update(self, dt):
        if self.finished:
            return
        self.frame_acc += dt
        if self.frame_acc < self.frame_interval:
            return
        adt = self.frame_acc
        self.frame_acc = 0.0
        if self.mode == "client" and self.client and self.phase != "lobby":
            state = self.client.get_state()
            if state:
                self._apply_remote_state(state)
            msg = self.client.get_server_msg()
            if msg:
                self._handle_server_msg(msg)
        if self.phase == "lobby":
            self.lobby_timer += adt
            if self.mode == "host":
                if self.server and self.server.client_connected.is_set():
                    dbg("LOBBY: Client da -> READY + MSG_READY")
                    self.network_ready = True
                    self.game.reset_match()
                    self.phase = "ready"
                    self.server.send_msg({"type": MSG_READY})
            elif self.mode == "client":
                if self.scan_result is True:
                    if not getattr(self, "_scan_logged", False):
                        self._scan_logged = True
                        dbg("LOBBY: Connect OK -> READY")
                    self.network_ready = True
                    self.phase = "ready"
                elif self.scan_result is False:
                    if not getattr(self, "_scan_logged", False):
                        self._scan_logged = True
                        dbg("LOBBY: Scan erfolglos -> ERROR-Screen")
                    self.lobby_msg = "NO ROOM FOUND!\nSAME WLAN?"
                    self.phase = "error"
            return
        if self.phase in ("error", "disconnect", "gameover", "ready", "paused"):
            if self.mode == "host" and self.server:
                if (self.phase in ("gameover", "paused")
                        and self.server.consume_restart_req()):
                    self._restart()
                elif (self.phase == "paused"
                        and self.server.consume_resume_req()):
                    self.phase = "playing"
                    self.server.send_msg({"type": MSG_RESUME})
            self._check_connection()
            return
        if self._check_connection():
            return
        if (self.mode == "host" and self.server
                and self.server.consume_restart_req()
                and self.phase == "playing"):
            self._restart()
            return
        self.play_time += adt
        held = self._poll_held()
        if self.mode in ("ai", "host"):
            p2_dir = 0
            if self.mode == "ai":
                p2_dir = self.ai.update(self.game.ball_x, self.game.ball_y,
                                        self.game.ball_vx, self.game.ball_vy,
                                        self.game.p2_x, adt)
            elif self.server:
                p2_dir = self.server.get_client_dir()
                if self.server.client_pet_key:
                    self.mascot["guest_key"] = self.server.client_pet_key
                if self.server.consume_pause_req():
                    self.phase = "paused"
                    self.pause_sel = 0
                    self.server.send_msg({"type": MSG_PAUSE})
                    return
            p1_dir = self.pulse_dir if self.pulse_dir else held
            self.pulse_dir = 0
            self.game.update(adt, p1_dir, p2_dir)
            self._mascot_hit_check(adt)
            if self.mode == "host" and self.server:
                st = self.game.get_state_dict()
                st["m_host_key"] = self.mascot.get("host_key")
                st["m_host_x"] = self.mascot.get("host_x")
                st["m_guest_x"] = self.mascot.get("guest_x")
                self.server.send_state(st)
            if self.game.state == "gameover":
                self._on_gameover()
        elif self.mode == "client" and self.client:
            if held != self._last_sent_dir:
                self.client.send_input(held)
                self._last_sent_dir = held
            self._pet_send_t -= adt
            if self._pet_send_t <= 0:
                self._pet_send_t = 0.5
                self.client.send_msg(
                    {"type": "pet", "key": self.pet.get_sprite_key()})
            state = self.client.get_state()
            if state:
                self._apply_remote_state(state)
            msg = self.client.get_server_msg()
            if msg:
                self._handle_server_msg(msg)

    def _check_connection(self):
        if self.mode == "host" and self.network_ready and self.server:
            if not self.server.client_connected.is_set():
                dbg("NET: Verbindung verloren (Host-Sicht)")
                self.phase = "disconnect"
                return True
        if self.mode == "client" and self.network_ready and self.client:
            if not self.client.connected.is_set():
                dbg("NET: Verbindung verloren (Client-Sicht)")
                self.phase = "disconnect"
                return True
        return False

    def _apply_remote_state(self, st):
        g = self.game
        g.p1_x = st.get("p1_x", g.p1_x)
        g.p2_x = st.get("p2_x", g.p2_x)
        g.ball_x = st.get("ball_x", g.ball_x)
        g.ball_y = st.get("ball_y", g.ball_y)
        g.score_p1 = st.get("score_p1", g.score_p1)
        g.score_p2 = st.get("score_p2", g.score_p2)
        g.state = st.get("state", g.state)
        if st.get("m_host_key"):
            self.mascot["host_key"] = st["m_host_key"]
        if st.get("m_host_x") is not None:
            self.mascot["host_x"] = st["m_host_x"]
        if st.get("m_guest_x") is not None:
            self.mascot["guest_x"] = st["m_guest_x"]
        if st.get("state") == "gameover":
            g.winner = st.get("winner", 0)
            self._on_gameover()
        elif st.get("state") == "playing" and self.phase == "ready":
            self.phase = "playing"

    def _handle_server_msg(self, msg):
        t = msg.get("type")
        if t == MSG_READY:
            self.game.reset_match()
            self.phase = "ready"
        elif t == MSG_START:
            self.game.start()
            self.phase = "playing"
        elif t == MSG_PAUSE:
            self.phase = "paused"
            self.pause_sel = 0
        elif t == MSG_RESUME:
            self.phase = "playing"
        elif t == MSG_RESTART:
            self.game.reset_match()
            self.phase = "ready"
        elif t == MSG_QUIT:
            self.phase = "disconnect"

    def _on_gameover(self):
        if self.phase == "gameover":
            return
        self.phase = "gameover"
        w = self.game.winner
        if self.mode == "ai":
            self.winner_text = "YOU WIN!" if w == 1 else "AI WINS!"
        elif self.mode == "host":
            self.winner_text = "YOU WIN!" if w == 1 else "GUEST WINS!"
        else:
            self.winner_text = "YOU WIN!" if w == 2 else "HOST WINS!"
        self._apply_pet_bonus(w)

    def _apply_pet_bonus(self, winner):
        if self._applied_pet_bonus:
            return
        self._applied_pet_bonus = True
        p = self.pet
        p._last_minigame = p.age
        p.play_count += 1
        p.state = "playing"
        p.state_timer = 0.0
        p.calling = False
        p.energy = max(0.0, p.energy - 8)
        won = (winner == 1) or (self.mode == "client" and winner == 2)
        if won:
            p.happiness = min(100.0, p.happiness + 15)
            p.weight = max(5, p.weight - 1.0)
        elif winner == 0:
            p.happiness = min(100.0, p.happiness + 5)
        else:
            p.happiness = min(100.0, p.happiness + 3)
        if self.play_time > 60:
            p.hunger = min(100.0, p.hunger + 5)

    # ---------------- INPUT ----------------
    def _press(self, d):
        if self.mode == "client" and self.client:
            self.client.send_input(d)
            self._last_sent_dir = d
        else:
            self.pulse_dir = d

    def _poll_held(self):
        g = self._game
        kp = pygame.key.get_pressed()
        left = bool(kp[pygame.K_a] or kp[pygame.K_LEFT])
        right = bool(kp[pygame.K_d] or kp[pygame.K_BACKSPACE])
        m = self._mouse_held_dir()
        if m == -1:
            left = True
        elif m == 1:
            right = True
        if (g is not None and pygame.mouse.get_pressed()[0]
                and getattr(g, "mouse_hold_btn", None) is not None):
            if g.mouse_hold_btn == 0:
                left = True
            elif g.mouse_hold_btn == 2:
                right = True
        if left and not right:
            return -1
        if right and not left:
            return 1
        return 0

    def _mouse_held_dir(self):
        g = self._game
        if g is None or not pygame.mouse.get_pressed()[0]:
            return 0
        mx, my = g.to_virtual(pygame.mouse.get_pos())
        for i, rect in enumerate(g.buttons):
            if rect.inflate(10, 10).collidepoint((mx, my)):
                return -1 if i == 0 else (1 if i == 2 else 0)
        return 0

    def _resume(self):
        self.phase = "playing"
        if self.mode == "client" and self.client:
            self.client.send_msg({"type": MSG_RESUME_REQ})
        elif self.mode == "host" and self.server:
            self.server.send_msg({"type": MSG_RESUME})

    def _restart_from_pause(self):
        if self.mode == "client" and self.client:
            self.client.send_msg({"type": MSG_RESTART_REQ})
        else:
            self._restart()

    def _cd_ok(self, btn, cd=0.3):
        now = time.time()
        if now - self._btn_cd.get(btn, -10.0) < cd:
            return False
        self._btn_cd[btn] = now
        return True

    def handle(self, btn):
        if self.finished:
            if btn == 1:
                self._cleanup()
            return
        if self.phase in ("error", "disconnect", "lobby"):
            if btn == 1:
                self._cleanup()
            return
        if self.phase == "blocked":
            if btn == 1:
                self.finished = True
            return
        if self.phase == "gameover":
            if btn == 0:
                self.gameover_sel = 0
            elif btn == 2:
                self.gameover_sel = 1
            elif btn == 1 and self._cd_ok(1, 0.5):
                if self.gameover_sel == 0:
                    if self.mode == "client" and self.client:
                        self.client.send_msg({"type": MSG_RESTART_REQ})
                    self._restart()
                else:
                    self._cleanup()
            return
        if self.phase == "ready":
            if btn == 1 and self._cd_ok(1, 0.5) and self.mode in ("ai", "host"):
                self.phase = "playing"
                self.game.start()
                if self.mode == "host" and self.server:
                    self.server.send_msg({"type": MSG_START})
            return
        if self.phase == "paused":
            if btn == 0 and self._cd_ok(0, 0.3):
                self.pause_sel = (self.pause_sel + 1) % 2
            elif btn == 2 and self._cd_ok(2, 0.3):
                self._resume()
            elif btn == 1 and self._cd_ok(1, 0.5):
                if self.pause_sel == 0:
                    self._restart_from_pause()
                else:
                    self._cleanup()
            return
        if self.phase == "playing":
            if btn == 0:
                self._press(-1)
            elif btn == 2:
                self._press(1)
            elif btn == 1 and self._cd_ok(1, 0.5):
                self.phase = "paused"
                self.pause_sel = 0
                if self.mode == "client" and self.client:
                    self.client.send_msg({"type": MSG_PAUSE_REQ})
                elif self.server:
                    self.server.send_msg({"type": MSG_PAUSE})

    def _restart(self):
        self.game.reset_match()
        self.phase = "ready"
        self.gameover_sel = 0
        self._applied_pet_bonus = False
        self.play_time = 0.0
        if self.mode == "host" and self.server:
            self.server.send_msg({"type": MSG_READY})

    def _cleanup(self):
        if self.server:
            self.server.send_msg({"type": MSG_QUIT})
            self.server.stop()
            self.server = None
        if self.client:
            self.client.send_msg({"type": MSG_QUIT})
            self.client.stop()
            self.client = None
        if not self._applied_pet_bonus and self.play_time > 5:
            self._apply_pet_bonus(0)
        try:
            pygame.key.set_repeat(*self._old_repeat)
        except Exception:
            pass
        self.finished = True

    # ---------------- RENDERING ----------------
    def _palette(self, game):
        """Farben wie im Hauptspiel: get_colors() invertiert bereits
        bei (outdoor+Nacht) und (indoor+Licht aus)."""
        c = game.get_colors()
        fg, bg = c["bg"], c["fg"]
        gr = tuple((a + b) // 2 for a, b in zip(bg, fg))
        return fg, bg, gr
    def _S(self, game):
        return max(1, game.surface.get_width() // 240)

    def draw(self, game):
        self._game = game
        game.surface.fill(game.get_colors()["fg"])
        if self.phase == "blocked":
            self._draw_blocked(game); return
        if self.phase == "lobby":
            self._draw_lobby(game); return
        if self.phase == "error":
            self._draw_error(game); return
        if self.phase == "disconnect":
            self._draw_disconnect(game); return
        self._draw_field(game)
        if self.phase == "gameover":
            self._draw_gameover(game)
        elif self.phase == "paused":
            self._draw_paused(game)
        elif self.phase == "ready":
            self._draw_ready(game)

    def _draw_field(self, game):
        S = self._S(game)
        surf = game.surface
        g = self.game
        OY = self.FIELD_OY
        W, B, GR = self._palette(game)

        t = game.font_big.render(f"{g.score_p2} : {g.score_p1}", True, W)
        surf.blit(t, t.get_rect(center=(120 * S, 15 * S)))

        field = pygame.Rect(0, OY * S, 240 * S, g.FIELD_H * S)
        pygame.draw.rect(surf, W, field, S)

        old_clip = surf.get_clip()
        surf.set_clip(field)

        if self.mode == "ai":
            tl, bl = "AI", "YOU"
        elif self.mode == "host":
            tl, bl = "GUEST", "YOU"
        else:
            tl, bl = "HOST", "YOU"
        t = game.font_small.render(tl, True, GR)
        surf.blit(t, (5 * S, (OY + 2) * S))
        t = game.font_small.render(bl, True, GR)
        surf.blit(t, (5 * S, (OY + g.FIELD_H - 10) * S))

        mid_y = OY + g.FIELD_H // 2
        for x in range(4, 240, 16):
            pygame.draw.rect(surf, GR, (x * S, mid_y * S, 8 * S, S))

        if self.mode in ("ai", "host"):
            bot_x, top_x = g.p1_x, g.p2_x
            ball_y = g.ball_y
        else:
            bot_x, top_x = g.p2_x, g.p1_x
            ball_y = g.FIELD_H - g.ball_y
        pw, ph = g.PADDLE_W * S, g.PADDLE_H * S
        pygame.draw.rect(surf, W, (int(top_x * S) - pw // 2,
                                   (OY + g.PADDLE_Y_TOP) * S, pw, ph))
        pygame.draw.rect(surf, W, (int(bot_x * S) - pw // 2,
                                   (OY + g.PADDLE_Y_BOT) * S, pw, ph))
        bs = g.BALL_SIZE * S
        pygame.draw.rect(surf, W, (int(g.ball_x * S) - bs // 2,
                                   int((OY + ball_y) * S) - bs // 2, bs, bs))
        self._draw_mascots(game)
        if g.state == "scored":
            t = game.font_huge.render("POINT!", True, W)
            surf.blit(t, t.get_rect(center=(120 * S, (OY + g.FIELD_H // 2) * S)))
        surf.set_clip(old_clip)
        # t = game.font_small.render("LEFT", True, GR)
        # surf.blit(t, (41 * S, 270 * S))
        # t = game.font_small.render("PAUSE", True, GR)
        # surf.blit(t, (106 * S, 270 * S))
        # t = game.font_small.render("RIGHT", True, GR)
        # surf.blit(t, (172 * S, 270 * S))
        game.draw_button_text("<-", "PAUSE", "->", W)

    def _overlay(self, game, alpha=170):
        S = self._S(game)
        ov = pygame.Surface((240 * S, 272 * S), pygame.SRCALPHA)
        bg = game.get_colors()["fg"]
        ov.fill((bg[0], bg[1], bg[2], alpha))
        game.surface.blit(ov, (0, 0))

    def _draw_ready(self, game):
        S = self._S(game)
        self._overlay(game, 140)
        t = game.font_huge.render("READY?", True, self._palette(game)[0])
        game.surface.blit(t, t.get_rect(center=(120 * S, 130 * S)))
        if int(time.time() * 2) % 2 == 0:
            hint = "B: START" if self.mode in ("ai", "host") else "WAIT FOR HOST"
            t = game.font_big.render(hint, True, self._palette(game)[0])
            game.surface.blit(t, t.get_rect(center=(120 * S, 165 * S)))

    def _draw_paused(self, game):
        S = self._S(game)
        surf = game.surface
        W, B, GR = self._palette(game)
        self._overlay(game, 200)
        t = game.font_huge.render("PAUSED", True, W)
        surf.blit(t, t.get_rect(center=(120 * S, 90 * S)))
        for i, opt in enumerate(("NEUSTART", "BEENDEN")):
            y = 130 + i * 30
            box = (70 * S, y * S, 100 * S, 22 * S)
            if i == self.pause_sel:
                pygame.draw.rect(surf, W, box)
                t = game.font_big.render(opt, True, B)
            else:
                pygame.draw.rect(surf, W, box, max(1, S // 2))
                t = game.font_big.render(opt, True, W)
            surf.blit(t, t.get_rect(center=(120 * S, (y + 11) * S)))
        t = game.font_small.render("A:WAHL  B:OK  C:WEITER", True, GR)
        surf.blit(t, t.get_rect(center=(120 * S, 210 * S)))

    def _draw_gameover(self, game):
        S = self._S(game)
        surf = game.surface
        W, B, GR = self._palette(game)
        self._overlay(game, 200)
        t = game.font_huge.render("GAME OVER", True, W)
        surf.blit(t, t.get_rect(center=(120 * S, 80 * S)))
        t = game.font_big.render(self.winner_text, True, W)
        surf.blit(t, t.get_rect(center=(120 * S, 112 * S)))
        t = game.font_big.render(f"{self.game.score_p2} : {self.game.score_p1}", True, GR)
        surf.blit(t, t.get_rect(center=(120 * S, 138 * S)))
        for i, opt in enumerate(("RESTART", "QUIT")):
            y = 165 + i * 30
            box = (70 * S, y * S, 100 * S, 22 * S)
            if i == self.gameover_sel:
                pygame.draw.rect(surf, W, box)
                t = game.font_big.render(opt, True, B)
            else:
                pygame.draw.rect(surf, W, box, max(1, S // 2))
                t = game.font_big.render(opt, True, W)
            surf.blit(t, t.get_rect(center=(120 * S, (y + 11) * S)))
        t = game.font_small.render("A/C: SELECT  B: OK", True, GR)
        surf.blit(t, t.get_rect(center=(120 * S, 240 * S)))

    def _draw_lobby(self, game):
        S = self._S(game)
        surf = game.surface
        W, B, GR = self._palette(game)
        t = game.font_huge.render("PONG", True, W)
        surf.blit(t, t.get_rect(center=(120 * S, 55 * S)))
        if self.mode == "host":
            t = game.font_big.render("HOST MODE", True, W)
            surf.blit(t, t.get_rect(center=(120 * S, 85 * S)))
            t = game.font.render(f"IP {get_local_ip()}:{PONG_PORT}", True, GR)
            surf.blit(t, t.get_rect(center=(120 * S, 110 * S)))
            t = game.font_big.render("WAITING" + "." * (int(time.time() * 2) % 4),
                                     True, W)
            surf.blit(t, t.get_rect(center=(120 * S, 150 * S)))
        else:
            t = game.font_big.render("JOIN MODE", True, W)
            surf.blit(t, t.get_rect(center=(120 * S, 85 * S)))
            t = game.font_big.render("SCANNING" + "." * (int(time.time() * 3) % 4),
                                     True, W)
            surf.blit(t, t.get_rect(center=(120 * S, 150 * S)))
            pct = min(1.0, self.lobby_timer / 8.0)
            pygame.draw.rect(surf, W, (40 * S, 175 * S, 160 * S, 8 * S), max(1, S // 2))
            if pct > 0.02:
                pygame.draw.rect(surf, W, (42 * S, 177 * S, int(156 * S * pct), 4 * S))
        t = game.font.render("B: CANCEL", True, GR)
        surf.blit(t, t.get_rect(center=(120 * S, 250 * S)))

    def _draw_blocked(self, game):
        S = self._S(game)
        t = game.font_huge.render(
            "ZZZ..." if self.blocked_reason == "sleep" else "WAIT!",
            True, self._palette(game)[0])
        game.surface.blit(t, t.get_rect(center=(120 * S, 120 * S)))
        t = game.font_big.render("B: OK", True, self._palette(game)[0])
        game.surface.blit(t, t.get_rect(center=(120 * S, 165 * S)))

    def _draw_error(self, game):
        S = self._S(game)
        surf = game.surface
        W, B, GR = self._palette(game)
        t = game.font_huge.render("ERROR", True, W)
        surf.blit(t, t.get_rect(center=(120 * S, 90 * S)))
        for i, line in enumerate((self.lobby_msg or "UNKNOWN").split("\n")):
            t = game.font.render(line, True, W)
            surf.blit(t, t.get_rect(center=(120 * S, (125 + i * 14) * S)))
        t = game.font_big.render("B: BACK", True, W)
        surf.blit(t, t.get_rect(center=(120 * S, 240 * S)))

    def _draw_disconnect(self, game):
        S = self._S(game)
        surf = game.surface
        W, B, GR = self._palette(game)
        t = game.font_huge.render("DISCONNECT", True, W)
        surf.blit(t, t.get_rect(center=(120 * S, 110 * S)))
        t = game.font.render("CONNECTION LOST", True, W)
        surf.blit(t, t.get_rect(center=(120 * S, 145 * S)))
        t = game.font_big.render("B: BACK", True, W)
        surf.blit(t, t.get_rect(center=(120 * S, 220 * S)))
