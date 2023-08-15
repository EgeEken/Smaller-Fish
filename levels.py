import pygame as pg
from pygame.locals import *
import sys
import copy
import random
import math

pg.init()
FPS = 60
FONT = pg.font.SysFont("comicsans", 20)

PLAYERVALS = {"gravity": 100,
              "waterlift": 100,
              "jump": 15,
              "jump_cooldown": 0.32,
              "speed": 50,
              "terminal": 200,
              "swimspeed": 30,
              "swimterminal": 150,
              "airdrag": 0.02 * FPS,
              "waterdrag": 0.04 * FPS,
              "grounddrag": 0.07 * FPS,
              "maxoxygen": 1000,
              "o2loss": 100,
              "gun": False,
              "gun_strength": 0.5}

PLAYERVALS2 = {"gravity": 100,
              "waterlift": 100,
              "jump": 15,
              "jump_cooldown": 0.32,
              "speed": 50,
              "terminal": 200,
              "swimspeed": 30,
              "swimterminal": 150,
              "airdrag": 0.02 * FPS,
              "waterdrag": 0.04 * FPS,
              "grounddrag": 0.07 * FPS,
              "maxoxygen": 1000,
              "o2loss": 100,
              "gun": True,
              "gun_strength": 0.5}

FISHVALS = {"gravity": 50,
            "airdrag": 0.4 * FPS,
            "maxoxygen": 300,
            "o2loss": 100}

VERYBIGFISHVALS = {"lunge_telegraph": 1,
                   "lunge_duration": 2}

GUNVALS = {"anim_freq": 2,
           "anim_range": 1}


class Character:
    def __init__(self, topleft, width, height, values=None, color=(255, 0, 0), image="char.png"):
        if values is None: values = PLAYERVALS.copy()
        try:
            self.image = pg.transform.scale(pg.image.load(image), (width, height))
            self.flipped = pg.transform.flip(self.image, True, False)
        except:
            print(f"Error loading character image {image}")
            self.image = None
        self.color = color

        self.topleft = pg.Vector2(topleft)
        self.startpos = pg.Vector2(topleft)
        self.width = width
        self.height = height
        self.pg_rect = pg.Rect(topleft, (width, height))  # hitbox
        self.values = values

        self.v = pg.Vector2(0, 0)

        self.alive = True
        self.gun: bool = values["gun"]
        self.can_jump = False

        self.ray_end: pg.Vector2 | None = None
        self.ray_start: pg.Vector2 | None = None
        self.ray_sprite = None
        self.gun_strength = values["gun_strength"]

        self.jump_cooldown = values["jump_cooldown"]  # in seconds
        self.jump_timer = 0  # jumping sets this to jump_cooldown, and every frame it decreases by dt until it reaches 0

        self.speed = values["speed"]  # in pixels per second, will need a lot of tweaking
        self.terminal = values["terminal"]
        self.airdrag = values["airdrag"]

        self.swimspeed = values["swimspeed"]
        self.swimterminal = values["swimterminal"]
        self.waterdrag = values["waterdrag"]

        self.grounddrag = values["grounddrag"]

        self.maxoxygen = values["maxoxygen"]
        self.oxygen = self.maxoxygen
        self.o2loss = values["o2loss"]

        self.gravity = values["gravity"]
        self.waterlift = values["waterlift"]
        self.jump = values["jump"]

        self.level: Level | None = None

    def move(self, newtopleft):
        self.topleft = pg.Vector2(newtopleft)
        self.pg_rect = pg.Rect(newtopleft, (self.width, self.height))

    def in_water(self, waterlevel):
        """Returns the percentage of the character's height that is in water"""
        if self.topleft[1] + self.height > waterlevel:
            return min((self.topleft[1] + self.height - waterlevel) / self.height, 1)
        return 0

    def shoot(self, mousepos):
        if not self.gun: return
        start = pg.Vector2(self.topleft + (self.width / 2, self.height / 2))
        end = start + pg.Vector2(pg.Vector2(mousepos) - start) * 50

        current_max = start.distance_squared_to(end)
        for rec in self.level.wallrects + list(
                [obj.pg_rect for obj in self.level.objects if isinstance(obj, Fish) and obj.alive]):
            if x := pg.Rect.clipline(rec, start, end):
                if (d := start.distance_squared_to(pg.Vector2(x[0]))) < current_max:
                    current_max = d
                    end = x[0]
                if (d := start.distance_squared_to(pg.Vector2(x[1]))) < current_max:
                    current_max = d
                    end = x[1]

        self.ray_start = start
        self.ray_end = end

    def inputs(self, dt, waterlevel):

        for event in pg.event.get():
            if event.type == QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE):
                pg.quit()
                sys.exit()
            # single click inputs, continuous inputs are handled below
            if self.in_water(waterlevel) < 1:
                if event.type == KEYDOWN and event.key == K_SPACE and self.can_jump:
                    self.can_jump = False
                    self.jump_timer = self.jump_cooldown
                    self.v.y = -self.jump

        keys = pg.key.get_pressed()
        # gravity
        self.v.y += self.gravity * dt
        # jump timer
        if self.jump_timer >= 0:
            self.jump_timer -= dt

        if self.in_water(waterlevel) > 0.4:
            # player head being in water drains oxygen
            if self.in_water(waterlevel) > 0.9:
                self.oxygen -= self.o2loss * dt
            # being in water resets jump
            if self.jump_timer <= 0:
                self.can_jump = True
            # water lift
            self.v.y -= self.waterlift * self.in_water(waterlevel) * dt
            # movement in water
            if keys[K_a]:  # left
                self.v.x -= self.swimspeed * dt
            if keys[K_d]:  # right
                self.v.x += self.swimspeed * dt
            if keys[K_w] or keys[K_SPACE]:  # up
                self.v.y -= self.swimspeed * dt
            if keys[K_s]:  # down
                self.v.y += self.swimspeed * dt

            # water drag
            self.v *= 1 - self.waterdrag * dt

            # terminal velocity in water
            self.v.x = max(-self.swimterminal, min(self.v.x, self.swimterminal))
            self.v.y = max(-self.swimterminal, min(self.v.y, self.swimterminal))

            # increase oxygen until max oxygen if not in water
        if self.in_water(waterlevel) < 0.9 and self.oxygen != self.maxoxygen:
            self.oxygen = min(self.oxygen + self.o2loss * 4 * dt, self.maxoxygen)
        else:
            # movement out of water
            if keys[K_a]:  # left
                self.v.x -= self.speed * dt
            if keys[K_d]:  # right
                self.v.x += self.speed * dt

            # air drag
            self.v *= 1 - self.airdrag * dt

            # terminal velocity out of water
            self.v.x = max(-self.terminal, min(self.v.x, self.terminal))
            self.v.y = max(-self.terminal, min(self.v.y, self.terminal))

        mouse = pg.mouse.get_pressed()
        if mouse[0]:
            self.shoot(pg.mouse.get_pos())
        else:
            self.ray_start = self.ray_end = None

    def reset(self):
        self.move(self.startpos)
        self.v = pg.Vector2(0, 0)
        self.oxygen = self.maxoxygen
        self.alive = True
        self.can_jump = False
        self.gun = self.values["gun"]


class Wall:
    def __init__(self, topleft, width, height, color=(0, 0, 0)):
        self.topleft = pg.Vector2(topleft)
        self.width = width
        self.height = height
        self.pg_rect: Rect = pg.Rect(topleft, (width, height))
        self.color = color
    
    def copy(self):
        return Wall(self.topleft, self.width, self.height, self.color)


class Object:
    def __init__(self, topleft, width, height, color, sprite=None):
        self.topleft = pg.Vector2(topleft)
        if color == "invis":
            self.color = (255, 255, 255, 0)
        else:
            self.color = pg.Vector3(color)

        self.startpos = pg.Vector2(topleft)
        self.startcolor = self.color
        self.startwidth = width
        self.startheight = height

        self.pg_rect = pg.Rect(topleft, (width, height))
        self.width = width
        self.height = height

        try:
            self.sprite = pg.transform.scale(pg.image.load(sprite), (width, height))
        except Exception:
            print(f"Error loading sprite: {sprite}")
            self.sprite = None

        self.sprites = [self.sprite]
        if self.sprite != None:
            self.flippedsprites = [pg.transform.flip(self.sprite, True, False)]
        else:
            self.flippedsprites = [None]
        self.spriteindex = 0

    def move(self, newtopleft):
        self.topleft = pg.Vector2(newtopleft)
        self.pg_rect = pg.Rect(newtopleft, (self.width, self.height))
        
    def resize(self, newwidth, newheight):
        self.width = newwidth
        self.height = newheight
        self.pg_rect = pg.Rect(self.topleft, (newwidth, newheight))
        if self.sprite != None:
            self.sprite = pg.transform.scale(self.sprite, (newwidth, newheight))
            for sprite in self.sprites:
                sprite = pg.transform.scale(sprite, (newwidth, newheight))
            for sprite in self.flippedsprites:
                sprite = pg.transform.scale(sprite, (newwidth, newheight))

    def reset(self):
        self.move(self.startpos)
        self.resize(self.startwidth, self.startheight)
        self.color = self.startcolor


class Gun(Object):
    def __init__(self, topleft, width, height, color, sprite, values):
        super().__init__(topleft, width, height, color, sprite)
        self.picked = False
        self.animation_frequency = values["anim_freq"]  # the frequency of the guns movement
        # (it moves up and down like a dropped item in mc lmao)
        self.animation_range = values["anim_range"]  # how many pixels the gun will go up and down
        self.animation_timer = 0

    def f(self, x):
        return pg.Vector2(0, math.sin(3.14 * x * self.animation_frequency) * self.animation_range)
    
    def animation(self, dt):
        if not self.picked:
            if self.animation_timer >= 1:
                self.animation_timer = 0
            self.move(self.topleft + self.f(self.animation_timer))
            self.animation_timer += dt
            
    def reset(self):
        self.picked = False
        self.animation_timer = 0
        super().reset()


class Button(Object):
    def __init__(self, topleft, width, height, color, sprite, buttontype, newlevel=0, wallind=0):
        super().__init__(topleft, width, height, color, sprite)
        self.pressed = False
        self.buttontype = buttontype
        self.newlevel = newlevel
        self.wallind = wallind

    def raisewater(self, level):
        level.waterlevel = self.newlevel

    def lowerwater(self, level):
        level.waterlevel = self.newlevel

    def removewall(self, level):
        if self.wallind == "last":
            level.walls.pop()
            level.wallrects.pop()
            return
        if self.wallind == "all":
            level.walls = []
            level.wallrects = []
            return
        if self.wallind >= len(level.walls):
            return
        level.walls.pop(self.wallind)
        level.wallrects.pop(self.wallind)

    def reset(self):
        self.pressed = False
        super().reset()


class Fish(Object):
    def __init__(self, topleft, width, height, color, sprite, values, speed, existed=True):
        super().__init__(topleft, width, height, color, sprite)

        self.existed = existed
        self.alive = True
        self.speed = speed
        self.v = pg.Vector2(0, 0)

        self.gravity = values["gravity"]
        self.airdrag = values["airdrag"]

        self.maxoxygen = values["maxoxygen"]
        self.o2loss = values["o2loss"]
        self.oxygen = self.maxoxygen

        self.big_range = self.width * 6
        self.small_range = self.width * 3

        self.fastspeed = self.speed * 3
        self.rushspeed = self.speed * 6

        self.normalsprite = pg.transform.scale(pg.image.load(sprite), (self.width, self.height))
        
        self.values = values

    def alg(self, level: 'Level', dt):
        self.v += pg.Vector2(random.random() * self.speed / 2 - self.speed / 4,
                             random.random() * self.speed / 2 - self.speed / 4) * 60 * dt
        if self.v.length_squared() != 0:
            self.v = self.v.normalize() * self.speed
            
    def shrink(self, level: 'Level', newwidth, newheight):
        self.resize(newwidth, newheight)
        if self.width < 50:
            if isinstance(self, VeryBigFish):
                self.alive = False
                level.objects.append(BigFish(self.topleft, self.width, self.height, self.color, "bigfish.png", self.values, self.speed*2, "bigfish_rush.png", False))
            if self.width < 30:
                if isinstance(self, BigFish):
                    self.alive = False
                    level.objects.append(SmallFish(self.topleft, self.width, self.height, self.color, "smallfish.png", self.values, self.speed*2, False))
                if self.width < 5:
                    self.alive = False
        

    def reset(self):
        if self.existed:
            self.v = pg.Vector2(0, 0)
            self.alive = True
            self.oxygen = self.maxoxygen
            super().reset()
        else:
            self.alive = False
            
            
class SmallFish(Fish):
    def __init__(self, topleft, width, height, color, sprite, values, speed, existed=True):
        super().__init__(topleft, width, height, color, sprite, values, speed, existed)

    def alg(self, level: 'Level', dt):

        if not self.alive:
            return

        if self.topleft.y <= level.waterlevel:
            self.v.y += self.gravity * dt
            if self.v.y < 0:
                self.v *= (1 - self.airdrag * dt)
            self.oxygen -= self.o2loss * dt
            if self.oxygen <= 0:
                self.alive = False
            return

        if self.oxygen < self.maxoxygen:
            self.oxygen += self.o2loss * 2 * dt

        if self.topleft.distance_to(level.player.topleft) < self.small_range:
            self.v = (self.topleft - level.player.topleft).normalize() * self.rushspeed
            return

        if self.topleft.distance_to(level.player.topleft) < self.big_range:
            self.v = (self.topleft - level.player.topleft).normalize() * self.fastspeed
            return

        super().alg(level, dt)


class BigFish(Fish):
    def __init__(self, topleft, width, height, color, sprite, values, speed, rushsprite="bigfish_rush.png", existed=True):
        super().__init__(topleft, width, height, color, sprite, values, speed, existed)
        try:
            self.rushsprite = pg.transform.scale(pg.image.load(rushsprite), (self.width, self.height))
            self.sprites.append(self.rushsprite)
            self.flippedsprites.append(pg.transform.flip(self.rushsprite, True, False))
        except Exception:
            print(f"Error loading sprite: {rushsprite}")
            self.rushsprite = None
            self.sprites.append(None)
            self.flippedsprites.append(None)

    def alg(self, level: 'Level', dt):

        if self.spriteindex != 0:
            self.spriteindex = 0

        if not self.alive:
            return

        if self.topleft.y <= level.waterlevel:
            self.v.y += self.gravity * dt
            if self.v.y < 0:
                self.v *= (1 - self.airdrag * dt)
            self.oxygen -= self.o2loss * dt
            if self.oxygen <= 0:
                self.alive = False
            return

        if self.oxygen < self.maxoxygen:
            self.oxygen += self.o2loss * 2 * dt

        if any([isinstance(obj, SmallFish) and obj.alive for obj in level.objects]):
            closest = 5000  # just a number longer than the longest possible distance
            closestfish = None
            for obj in level.objects:
                dist = self.topleft.distance_to(obj.topleft)
                if isinstance(obj, SmallFish) and obj.alive and dist < closest:
                    closest = dist
                    closestfish = obj

            if closest < self.width / 2 + closestfish.width / 2:
                # self.spriteindex = 1 # rush sprite
                closestfish.v = pg.Vector2(0, 0)
                closestfish.alive = False
                return
            elif closest < self.small_range:
                if self.spriteindex != 1:
                    self.spriteindex = 1  # rush sprite
                self.v = pg.Vector2(closestfish.topleft - self.topleft).normalize() * self.rushspeed
                return
            elif closest < self.big_range:
                self.v = pg.Vector2(closestfish.topleft - self.topleft).normalize() * self.fastspeed
                return

        super().alg(level, dt)


class VeryBigFish(Fish):
    def __init__(self, topleft, width, height, color, sprite, values, fishvalues, speed,
                 lungesprite="verybigfish_lunge.png", existed=True):
        super().__init__(topleft, width, height, color, sprite, values=fishvalues, speed=speed, existed=existed)
        try:
            self.lungesprite = pg.transform.scale(pg.image.load(lungesprite), (self.width, self.height))
            self.sprites.append(self.lungesprite)
            self.flippedsprites.append(pg.transform.flip(self.lungesprite, True, False))
        except Exception:
            print(f"Error loading sprite: {lungesprite}")
            self.lungesprite = None
            self.sprites.append(None)
            self.flippedsprites.append(None)

        self.lungedistance = self.width * 2
        self.lungespeed = self.speed * 10

        self.lunge_duration = values["lunge_duration"]
        self.lunge_telegraph = values["lunge_telegraph"]
        self.lunge_timer = self.lunge_telegraph

    def alg(self, level: 'Level', dt):

        if not self.alive:
            return

        if self.spriteindex != 0:
            self.spriteindex = 0

        if self.topleft.y <= level.waterlevel:
            self.v.y += self.gravity * dt
            if self.v.y < 0:
                self.v *= (1 - self.airdrag * dt)
            self.oxygen -= self.o2loss * dt
            if self.oxygen <= 0:
                self.alive = False
            return

        if self.oxygen < self.maxoxygen:
            self.oxygen += self.o2loss * 2 * dt

        player = level.player
        if player.in_water(level.waterlevel) > 0 and self.topleft.distance_to(player.topleft) < self.big_range:
            if self.topleft.distance_to(player.topleft) > self.lungedistance:
                self.spriteindex = 0
                self.lunge_timer = self.lunge_telegraph
                self.color = self.startcolor
                self.v = pg.Vector2(player.topleft - self.topleft).normalize() * self.speed * 2
                return
            else:
                self.spriteindex = 1
                self.lunge(player.topleft, dt)
                return

        elif any([(isinstance(obj, SmallFish) or isinstance(obj, BigFish)) and obj.alive for obj in level.objects]):
            closest = 5000  # just a number longer than the longest possible distance
            closestfish = None
            for obj in level.objects:
                dist = self.topleft.distance_to(obj.topleft)
                if (isinstance(obj, SmallFish) or
                        isinstance(obj, BigFish)) and obj.alive and dist < closest:
                    closest = dist
                    closestfish = obj
            if closest < self.width / 2 + closestfish.width / 2:
                closestfish.v = pg.Vector2(0, 0)
                closestfish.alive = False
            elif closest < self.small_range:
                self.spriteindex = 1
                self.v = pg.Vector2(closestfish.topleft - self.topleft).normalize() * self.rushspeed
                return
            elif closest < self.big_range:
                self.v = pg.Vector2(closestfish.topleft - self.topleft).normalize() * self.fastspeed
                return

        super().alg(level, dt)

    def lunge(self, target, dt):
        if self.lunge_timer <= 0.1:
            self.spriteindex = 1
            self.lunge_timer = self.lunge_telegraph + self.lunge_duration
            self.color = self.startcolor
            self.v = pg.Vector2(target - self.topleft).normalize() * self.speed * 8
        elif self.lunge_timer <= self.lunge_telegraph:
            self.spriteindex = 0
            self.v = pg.Vector2(target - self.topleft).normalize() * self.speed * 0.01
        self.lunge_timer -= dt
        self.color = self.color + ((200, 20, 0) - self.startcolor) * (dt / self.lunge_telegraph)
        if self.color[0] > 230 or self.color[1] < 10:
            self.color = pg.Vector3(200, 20, 0)
        
    
    def reset(self):
        self.lunge_timer = self.lunge_telegraph
        super().reset()


class Level:
    def __init__(self, levelid, char, walls: list[Wall], objects: list[Object], screenwidth=500, screenheight=500, waterlevel=100, text=None, textpos=(0,0)):
        self.screenwidth = screenwidth
        self.screenheight = screenheight
        self.levelid = levelid  # short text description of the level or a number maybe like "1_base" "7_fish" "10_selfshrink" etc
        self.player: Character = char  # the player character, contains a top left position for the char object to start in, and a hitbox width and height
        self.player.level = self
        self.walls: list[Wall] = walls  # list of walls, each wall contains a starting point (top left), a width, a height, and a color
        self.wallrects: list[Rect] = [wall.pg_rect for wall in walls]
        self.objects: list[Object] = objects  # list of non-wall objects, each object contains top left position, a width and height and color for the hitbox, and a sprite
        self.waterlevel = waterlevel  # the height of the water level, above this y value (so lower on the screen) is water and above it is air
        self.cleared = False  # whether the level has been cleared or not
        self.copies = [[wall.copy() for wall in walls], waterlevel]
        self.text = text
        self.textpos = textpos

    def check_player_wall_collisions(self):
        X_newrect = pg.Rect(self.player.topleft + (self.player.v.x, 0), (self.player.width, self.player.height))
        Y_newrect = pg.Rect(self.player.topleft + (0, self.player.v.y), (self.player.width, self.player.height))
        XY_newrect = pg.Rect(self.player.topleft + self.player.v,
                             (self.player.width, self.player.height))  # corner clip fix
        res = [False, False, False, False]
        x_check = pg.Rect.collidelist(X_newrect, self.wallrects)
        y_check = pg.Rect.collidelist(Y_newrect, self.wallrects)
        # not corner
        if x_check != -1 or y_check != -1:
            # left-right
            if x_check != -1:
                # left
                if self.player.topleft[0] <= 0 or self.player.v.x < 0:
                    res[0] = True
                # right
                else:
                    res[1] = True
            # up-down
            if y_check != -1:
                # up
                if self.player.topleft[1] - self.player.height <= 0 or self.player.v.y < 0:
                    res[2] = True
                # down
                else:
                    res[3] = True

        # corner
        elif pg.Rect.collidelist(XY_newrect, self.wallrects) != -1:
            # up-left
            if self.player.v.x <= 0 and self.player.v.y <= 0:
                res[0] = True
                res[2] = True
            # up-right
            elif self.player.v.x >= 0 and self.player.v.y <= 0:
                res[1] = True
                res[2] = True
            # down-left
            elif self.player.v.x <= 0 and self.player.v.y >= 0:
                res[0] = True
                res[3] = True
            # down-right
            elif self.player.v.x >= 0 and self.player.v.y >= 0:
                res[1] = True
                res[3] = True

        return res

    def check_player_object_collisions(self):
        for obj in self.objects:
            if self.player.pg_rect.colliderect(obj.pg_rect):
                if isinstance(obj, VeryBigFish) and obj.alive:
                    self.player.alive = False
                if isinstance(obj, Gun) and not obj.picked:
                    self.player.gun = True
                    obj.picked = True
                if isinstance(obj, Button) and not obj.pressed:
                    obj.pressed = True
                    if obj.buttontype == "raisewater":
                        obj.raisewater(self)
                    elif obj.buttontype == "lowerwater":
                        obj.lowerwater(self)
                    elif obj.buttontype == "removewall":
                        obj.removewall(self)

        return False

    def check_object_wall_collisions(self, obj, dt):
        X_newrect = pg.Rect(obj.topleft + (obj.v.x * 60 * dt, 0), (obj.width, obj.height))
        Y_newrect = pg.Rect(obj.topleft + (0, obj.v.y * 60 * dt), (obj.width, obj.height))
        res = [False, False, False, False]
        # left-right
        if pg.Rect.collidelist(X_newrect, self.wallrects) != -1:
            # left
            if obj.topleft[0] <= 0 or obj.v.x < 0:
                res[0] = True
            # right
            else:
                res[1] = True
        if pg.Rect.collidelist(Y_newrect, self.wallrects) != -1:
            # up
            if obj.topleft[1] - obj.height <= 0 or obj.v.y < 0:
                res[2] = True
            # down
            else:
                res[3] = True
        return res

    def reset(self):
        self.player.reset()

        for obj in self.objects:
            obj.reset()

        self.cleared = False
        self.walls = self.copies[0]
        self.wallrects = [wall.pg_rect for wall in self.copies[0]]
        self.waterlevel = self.copies[1]

    def update(self, dt):

        # ----- PLAYER INPUTS / MOVEMENT -----

        self.player.inputs(dt, self.waterlevel)
        
        if self.player.gun and self.player.ray_end != None:
            for obj in self.objects:
                if obj.pg_rect.collidepoint(self.player.ray_end):
                    if isinstance(obj, Fish) and obj.alive:
                        newwidth = obj.width - obj.width * self.player.gun_strength * dt
                        newheight = obj.height - obj.height * self.player.gun_strength * dt
                        obj.shrink(self, newwidth, newheight)
                        

        # PLAYER WALL COLLISION DETECTION

        collisions = self.check_player_wall_collisions()

        if any(collisions):
            # left collision
            if collisions[0]:
                self.player.v.y *= (1 - self.player.grounddrag * dt)
                self.player.v.x = max(0, self.player.v.x)
            # right collision
            if collisions[1]:
                self.player.v.y *= (1 - self.player.grounddrag * dt)
                self.player.v.x = min(0, self.player.v.x)
            # up collision
            if collisions[2]:
                self.player.v.x *= (1 - self.player.grounddrag * dt)
                self.player.v.y = max(0, self.player.v.y)
            # down collision
            if collisions[3]:
                self.player.v.x *= (1 - self.player.grounddrag * 2 * dt)
                self.player.v.y = min(0, self.player.v.y)
                # touching the ground resets jump
                if self.player.jump_timer <= 0:
                    self.player.can_jump = True

        # ----- OBJECT PATHFINDING / MOVEMENT -----

        for obj in self.objects:
            if isinstance(obj, Fish):
                obj.alg(self, dt)
            if isinstance(obj, Gun):
                obj.animation(dt)

        # OBJECT WALL COLLISION DETECTION

        for i, obj in enumerate(self.objects):
            if isinstance(obj, Fish):
                collisions = self.check_object_wall_collisions(obj, dt)
                if any(collisions):
                    # left-right collision
                    if any(collisions[0:2]):
                        obj.v.x = -obj.v.x
                    # up-down collision
                    if any(collisions[2:4]):
                        obj.v.y = -obj.v.y

        self.check_player_object_collisions()

        if self.player.oxygen <= 0:
            self.player.alive = False

        self.player.move(self.player.topleft + self.player.v)
        
        

        for obj in self.objects:
            if isinstance(obj, Fish):
                obj.move(obj.topleft + obj.v)

        if self.player.topleft[0] + self.player.width > self.screenwidth:
            self.cleared = True
        
        elif self.player.topleft[1] > self.screenheight:
            self.player.alive = False


level0 = Level("0_base",
               Character((5, 5), 40, 40, PLAYERVALS, (255, 0, 0), "char.png"),
               [
                   Wall((0, 90), 65, 500),
                   Wall((435, 88), 65, 412),
                   Wall((0, 450), 500, 50),
                   Wall((0, 0), 1, 100)
               ],
               [],
               500,
               500,
               100,
               text = FONT.render(f"Level 1: Learn to swim!", True, (255, 0, 0)),
               textpos = (0, 0)
                )

level1 = Level("1_onewall",
               Character((5, 5), 40, 40, PLAYERVALS, (255, 0, 0), "char.png"),
               [
                   Wall((0, 90), 65, 500),
                   Wall((435, 88), 65, 412),
                   Wall((0, 450), 500, 50),
                   Wall((0, 0), 1, 100),
                   Wall((230, 0), 40, 350)
               ],
               [],
               500,
               500,
               100,
               text = FONT.render(f"Level 2: Learn to dive!", True, (255, 0, 0)),
               textpos = (0, 0)
                )

level2 = Level("2_threewalls",
               Character((5, 5), 40, 40, PLAYERVALS, (255, 0, 0), "char.png"),
               [
                   Wall((0, 90), 65, 500),
                   Wall((435, 88), 65, 412),
                   Wall((0, 450), 500, 50),
                   Wall((0, 0), 1, 100),
                   Wall((120, 0), 40, 350),
                   Wall((350, 0), 40, 350),
                   Wall((230, 90), 40, 410)
               ],
               [],
               500,
               500,
               100,
               text = FONT.render(f"Level 3: Learn to navigate!", True, (255, 0, 0)),
               textpos = (0, 0)
                )

level3 = Level("3_onesmallfish",
               Character((5, 5), 40, 40, PLAYERVALS, (255, 0, 0), "char.png"),
               [
                   Wall((0, 90), 65, 500),
                   Wall((435, 88), 65, 412),
                   Wall((0, 450), 500, 50),
                   Wall((0, 0), 1, 100)
               ],
               [
                   SmallFish((240, 240), 15, 15, (0, 255, 0), "smallfish.png", values=FISHVALS, speed=1.5)
               ],
               500,
               500,
               100,
               text = FONT.render(f"Level 4: Observe cute little fish!", True, (255, 0, 0)),
               textpos = (0, 0)
                )

level4 = Level("4_threesmallfish",
               Character((5, 5), 40, 40, PLAYERVALS, (255, 0, 0), "char.png"),
               [
                   Wall((0, 90), 65, 500),
                   Wall((435, 88), 65, 412),
                   Wall((0, 450), 500, 50),
                   Wall((0, 0), 1, 100)
               ],
               [
                   SmallFish((240, 240), 15, 15, (0, 255, 0), "smallfish.png", values=FISHVALS, speed=1.5),
                   SmallFish((130, 200), 25, 25, (20, 225, 0), "smallfish.png", values=FISHVALS, speed=1.3),
                   SmallFish((340, 350), 22, 22, (30, 205, 20), "smallfish.png", values=FISHVALS, speed=1.4)
               ],
               500,
               500,
               100,
               text = FONT.render(f"Level 5: Observe many cute little fishes!", True, (255, 0, 0)),
               textpos = (0, 0)
                )

level5 = Level("5_bigfish_smallfish",
               Character((5, 5), 40, 40, PLAYERVALS, (255, 0, 0), "char.png"),
               [
                   Wall((0, 90), 65, 500),
                   Wall((435, 88), 65, 412),
                   Wall((0, 450), 500, 50),
                   Wall((0, 0), 1, 100)
               ],
               [
                   SmallFish((240, 240), 15, 15, (0, 255, 0), "smallfish.png", values=FISHVALS, speed=1.5),
                   BigFish((75, 130), 50, 50, (200, 155, 0), "bigfish.png", values=FISHVALS, speed=0.6,
                           rushsprite="bigfish_rush.png")
               ],
               500,
               500,
               100,
               text = FONT.render(f"Level 6: Learn a valuable life lesson!", True, (255, 0, 0)),
               textpos = (0, 0)
                )

level6 = Level("6_feeding",
               Character((5, 5), 40, 40, PLAYERVALS, (255, 0, 0), "char.png"),
               [
                   Wall((0, 90), 65, 510),
                   Wall((535, 88), 65, 512),
                   Wall((0, 550), 600, 50),
                   Wall((0, 0), 1, 200),
               ],
               [
                   BigFish((300, 300), 40, 40, (200, 155, 0), "bigfish.png", values=FISHVALS, speed=0.6,
                           rushsprite="bigfish_rush.png"),
                   SmallFish((240, 240), 10, 10, (0, 255, 0), "smallfish.png", values=FISHVALS, speed=1.5),
                   SmallFish((120, 240), 10, 10, (0, 255, 0), "smallfish.png", values=FISHVALS, speed=1.5),
                   SmallFish((130, 100), 15, 15, (20, 150, 50), "smallfish.png", values=FISHVALS, speed=1.5),
                   SmallFish((340, 350), 12, 12, (40, 200, 10), "smallfish.png", values=FISHVALS, speed=1.5),
                   SmallFish((500, 400), 10, 10, (0, 255, 0), "smallfish.png", values=FISHVALS, speed=1.5),
               ],
               600,
               600,
               100,
               text = FONT.render(f"Level 7: Learn many valuable life lessons!", True, (255, 0, 0)),
               textpos = (0, 0)
                )

level7 = Level("7_cage",
               Character((5, 5), 30, 30, PLAYERVALS, (255, 0, 0), "char.png"),
               [
                   Wall((0, 90), 65, 810),
                   Wall((835, 88), 65, 812),
                   Wall((0, 850), 900, 50),
                   Wall((0, 0), 1, 200),
                   Wall((150, 150), 450, 10),
                   Wall((150, 150), 10, 450),
                   Wall((600, 150), 10, 450),
                   Wall((150, 600), 460, 10),
               ],
               [
                   VeryBigFish((450, 450), 120, 90, (130, 50, 0), "verybigfish.png",
                               values=VERYBIGFISHVALS, fishvalues=FISHVALS, speed=.8, lungesprite="verybigfish_lunge.png"),
                   BigFish((350, 300), 40, 40, (150, 155, 0), "bigfish.png", values=FISHVALS, speed=1,
                           rushsprite="bigfish_rush.png"),
                   SmallFish((240, 240), 10, 10, (0, 255, 0), "smallfish.png", values=FISHVALS, speed=1.5),
                   SmallFish((220, 370), 10, 10, (0, 210, 30), "smallfish.png", values=FISHVALS, speed=1.5),
                   SmallFish((305, 820), 10, 10, (0, 255, 0), "smallfish.png", values=FISHVALS, speed=1.5),
               ],
               900,
               900,
               100,
               text = FONT.render(f"Level 8: Appreciate the value of cages!", True, (255, 0, 0)),
               textpos = (0, 0)
                )


level8 = Level("8_brokencage",
               Character((5, 5), 20, 20, PLAYERVALS, (255, 0, 0), "char.png"),
               [Wall((0, 90), 65, 810),
                Wall((835, 88), 65, 812),
                Wall((0, 850), 900, 50),
                Wall((0, 0), 1, 200),
                Wall((150, 150), 450, 10),
                Wall((150, 150), 10, 450),
                Wall((600, 150), 10, 100),
                Wall((600, 500), 10, 100),
                Wall((150, 600), 460, 10),
                Wall((600, 250), 20, 10),
                Wall((600, 500), 20, 10),
                ],
               [VeryBigFish((380, 350), 120, 90, (130, 50, 0), "verybigfish.png", values=VERYBIGFISHVALS, fishvalues=FISHVALS, speed=.5, lungesprite="verybigfish_lunge.png"),
                SmallFish((700, 350), 10, 10,  (0, 255, 0), "smallfish.png", values=FISHVALS, speed=1.5),
                SmallFish((600, 300), 10, 10, (0, 255, 0), "smallfish.png", values=FISHVALS, speed=2),
                SmallFish((650, 330), 10, 10, (0, 255, 0), "smallfish.png", values=FISHVALS, speed=2),
                SmallFish((680, 430), 10, 10, (0, 255, 0), "smallfish.png", values=FISHVALS, speed=2),
                BigFish((500, 400), 30, 30, (150, 205, 0), "bigfish.png", values=FISHVALS, speed=1),
                SmallFish((450, 450), 12, 12, (40, 220, 10), "smallfish.png", values=FISHVALS, speed=1.5),
                SmallFish((500, 400), 10, 10, (0, 255, 0), "smallfish.png", values=FISHVALS, speed=1.5),
                ],
               900,
               900,
               100,
               text = FONT.render(f"Level 9: Appreciate the value of cages more!", True, (255, 0, 0)),
               textpos = (0, 0)
                )

level9 = Level("9_parkour",
               Character((5, 5), 20, 20, PLAYERVALS, (255, 0, 0), "char.png"),
               [
                   Wall((0, 90), 65, 810),
                    Wall((835, 88), 65, 812),
                    Wall((0, 850), 900, 50),
                    Wall((0, 0), 1, 200),
                    Wall((100, 70), 50, 10),
                    Wall((250, 70), 50, 10),
                    Wall((400, 70), 50, 10),
                    Wall((550, 70), 50, 10),
                    Wall((700, 70), 50, 10)
                ],
               [
                   VeryBigFish((150, 250), 90, 90, (140, 155, 0), "verybigfish.png", values=VERYBIGFISHVALS, fishvalues=FISHVALS, speed=.5, lungesprite="verybigfish_lunge.png"),
                    VeryBigFish((350, 440), 230, 190, (200, 105, 0), "verybigfish.png", values=VERYBIGFISHVALS, fishvalues=FISHVALS, speed=.6, lungesprite="verybigfish_lunge.png"),
                    VeryBigFish((650, 380), 160, 125, (200, 155, 0), "verybigfish.png", values=VERYBIGFISHVALS, fishvalues=FISHVALS, speed=.5, lungesprite="verybigfish_lunge.png"),
                    VeryBigFish((500, 400), 130, 100, (200, 205, 0), "verybigfish.png", values=VERYBIGFISHVALS, fishvalues=FISHVALS, speed=.4, lungesprite="verybigfish_lunge.png"),
                ],
               900,
               900,
               150,
               text = FONT.render(f"Level 10: Hone your platforming skills!", True, (255, 0, 0)),
               textpos = (0, 0)
                )


level10 = Level("10_fishdie",
                Character((5, 5), 20, 20, PLAYERVALS, (255, 0, 0), "char.png"),
                [
                    Wall((0, 90), 65, 810),
                    Wall((835, 88), 65, 812),
                    Wall((0, 850), 900, 50),
                    Wall((0, 0), 1, 200),
                    Wall((100, 70), 50, 10),
                    Wall((250, 70), 50, 10),
                    Wall((400, 70), 50, 10),
                    Wall((0, 850), 900, 50),
                    Wall((65, 205), 50, 10),
                    Wall((65, 150), 50, 10)
                ],
                [
                    VeryBigFish((350, 440), 190, 190, (200, 105, 0), "verybigfish.png", values=VERYBIGFISHVALS, fishvalues=FISHVALS, speed=.8, lungesprite="verybigfish_lunge.png"),
                    VeryBigFish((650, 380), 125, 125, (200, 155, 0), "verybigfish.png", values=VERYBIGFISHVALS, fishvalues=FISHVALS, speed=.8, lungesprite="verybigfish_lunge.png"),
                    VeryBigFish((500, 400), 100, 100, (200, 205, 0), "verybigfish.png", values=VERYBIGFISHVALS, fishvalues=FISHVALS, speed=.8, lungesprite="verybigfish_lunge.png"),
                    Button((65, 190), 15, 15, (240, 240, 240), None, "lowerwater", newlevel=900),
                    Button((800, 834), 15, 15, (20, 20, 240), None, "raisewater", newlevel=90)
                ],
                900,
                900,
                150,
                text = FONT.render(f"Level 11: Buttons 101!", True, (255, 0, 0)),
                textpos = (0, 0)
                )

level11 = Level("11_blocked",
                Character((5, 5), 20, 20, PLAYERVALS, (255, 0, 0), "char.png"),
                [
                    Wall((0, 90), 65, 810),
                    Wall((835, 88), 65, 812),
                    Wall((0, 850), 900, 50),
                    Wall((0, 0), 1, 200),
                    Wall((100, 70), 50, 10),
                    Wall((250, 70), 50, 10),
                    Wall((400, 70), 50, 10),
                    Wall((0, 850), 900, 50),
                    Wall((830, 20), 8, 100),
                    Wall((823, 20), 8, 100),
                    Wall((815, 20), 8, 100),
                ],
                [
                    VeryBigFish((350, 440), 190, 190, (200, 105, 0), "verybigfish.png", values=VERYBIGFISHVALS, fishvalues=FISHVALS, speed=.8, lungesprite="verybigfish_lunge.png"),
                    VeryBigFish((650, 380), 125, 125, (200, 155, 0), "verybigfish.png", values=VERYBIGFISHVALS, fishvalues=FISHVALS, speed=.8, lungesprite="verybigfish_lunge.png"),
                    VeryBigFish((500, 400), 100, 100, (200, 205, 0), "verybigfish.png", values=VERYBIGFISHVALS, fishvalues=FISHVALS, speed=.8, lungesprite="verybigfish_lunge.png"),
                    Button((65, 490), 25, 25, (60, 0, 60), None, "removewall", newlevel=None, wallind=10),
                    Button((450, 824), 25, 25, (60, 0, 60), None, "removewall", newlevel=None, wallind=9),
                    Button((810, 490), 25, 25, (60, 0, 60), None, "removewall", newlevel=None, wallind=8)
                ],
                900,
                900,
                110,
                text = FONT.render(f"Level 12: Buttons 102!", True, (255, 0, 0)),
                textpos = (0, 0)
                )

level12 = Level("12_gun_pickup",
                Character((5, 5), 20, 20, PLAYERVALS, (255, 0, 0), "char.png"),
                [
                    Wall((0, 90), 65, 810),
                    Wall((835, 0), 65, 300),
                    Wall((835, 500), 65, 400),
                    Wall((0, 850), 900, 50),
                    Wall((0, 0), 1, 200),
                    Wall((100, 70), 50, 10),
                    Wall((270, 70), 50, 10),
                    Wall((430, 80), 70, 10),
                    Wall((0, 850), 900, 50),
                    Wall((815, 300), 8, 200)
                ],
                [
                    VeryBigFish((200, 150), 190, 190, (200, 105, 0), "verybigfish.png", values=VERYBIGFISHVALS, fishvalues=FISHVALS, speed=.8, lungesprite="verybigfish_lunge.png"),
                    Gun((450, 30), 30, 30, (100, 100, 100), "gun.png", values=GUNVALS),
                    Button((390, 30), 50, 50, "invis", None, "removewall", newlevel=None, wallind=8),
                    Button((490, 30), 50, 50, "invis", None, "removewall", newlevel=None, wallind=8),
                ],
                900,
                900,
                110,
                text = FONT.render(f"Level 13: Shrink Ray 101!     Hold left click to shoot", True, (255, 0, 0)),
                textpos = (0, 0)
                )

# USE PLAYERVALS2 FROM NOW ON

level13 = Level("13_gun",
                Character((5, 330), 20, 20, PLAYERVALS2, (255, 0, 0), "char.png"),
                [   
                    Wall((0, 250), 1, 300),
                    Wall((0, 0), 360, 300),
                    Wall((0, 375), 360, 600),
                    Wall((320, 500), 600, 500),
                    Wall((0, 0), 1, 200),
                    Wall((631, 375), 300, 300),
                    Wall((357, 165), 90, 30),
                    Wall((557, 165), 90, 30),
                    Wall((633, 0), 300, 300)
                ],
                [
                    VeryBigFish((400, 220), 200, 200, (200, 105, 0), "verybigfish.png", values=VERYBIGFISHVALS, fishvalues=FISHVALS, speed=.3, lungesprite="verybigfish_lunge.png"),
                    SmallFish((400, 30), 20, 20, (0, 0, 255), "smallfish.png", values=FISHVALS, speed=1.5),
                    SmallFish((450, 40), 20, 20, (0, 0, 255), "smallfish.png", values=FISHVALS, speed=1.5),
                    SmallFish((500, 50), 20, 20, (0, 0, 255), "smallfish.png", values=FISHVALS, speed=1.5),
                    SmallFish((550, 60), 20, 20, (0, 0, 255), "smallfish.png", values=FISHVALS, speed=1.5),
                ],
                900,
                900,
                0,
                text = FONT.render(f"Level 14: Shrink Ray 102!", True, (255, 0, 0)),
                textpos = (0, 0)
                )

level14 = Level("14_whichbutton",
                Character((5, 330), 20, 20, PLAYERVALS2, (255, 0, 0), "char.png"),
                [
                    Wall((0, 250), 1, 300),
                    Wall((0, 0), 360, 300),
                    Wall((0, 375), 360, 600),
                    Wall((0, 0), 1, 200),
                    Wall((631, 375), 300, 600),
                    Wall((633, 0), 300, 300),
                    Wall((815, 300), 8, 200)
                ],
                [
                    VeryBigFish((400, -50), 200, 200, (200, 105, 0), "verybigfish.png", values=VERYBIGFISHVALS, fishvalues=FISHVALS, speed=.3, lungesprite="verybigfish_lunge.png"),
                    SmallFish((400, 0), 20, 20, (0, 0, 255), "smallfish.png", values=FISHVALS, speed=1),
                    Button((359, 400), 50, 50, (240, 240, 240), None, "lowerwater", newlevel=900, wallind=0),
                    Button((582, 400), 50, 50, (60, 0, 60), None, "removewall", newlevel=None, wallind=6)
                ],
                900,
                900,
                0,
                text = FONT.render(f"Level 15: Buttons final exam, hope you paid attention in 101!", True, (255, 0, 0)),
                textpos = (0, 0)
                )

level15 = Level("15_bruh",
                Character((5, 350), 20, 20, PLAYERVALS2, (255, 0, 0), "char.png"),
                [
                    Wall((0, 0), 1, 300),
                    Wall((0, 0), 900, 300),
                    Wall((0, 500), 900, 400),
                ],
                [   
                    SmallFish((400, 400), 20, 20, (0, 0, 255), "smallfish.png", values=FISHVALS, speed=1),
                 ],
                900,
                900,
                400,
                text = FONT.render(f"Level 16: Realise the game jam ends in 9th of august not 10", True, (255, 0, 0)),
                textpos = (0, 300)
                )

level16 = Level("16_bruh2",
                Character((5, 350), 20, 20, PLAYERVALS2, (255, 0, 0), "char.png"),
                [
                    Wall((0, 0), 1, 300),
                    Wall((0, 0), 900, 300),
                    Wall((0, 500), 900, 400),
                ],
                [   
                    SmallFish((400, 400), 20, 20, (0, 0, 255), "smallfish.png", values=FISHVALS, speed=1),
                 ],
                900,
                900,
                400,
                text = FONT.render(f"Level 17: Realise the game jam ends in 40 minutes holy shit", True, (255, 0, 0)),
                textpos = (0, 300)
                )

level17 = Level("17_bruh3",
                Character((5, 350), 20, 20, PLAYERVALS2, (255, 0, 0), "char.png"),
                [
                    Wall((0, 0), 1, 300),
                    Wall((0, 0), 900, 300),
                    Wall((0, 500), 900, 400),
                ],
                [   
                    SmallFish((400, 400), 20, 20, (0, 0, 255), "smallfish.png", values=FISHVALS, speed=1),
                 ],
                900,
                900,
                400,
                text = FONT.render(f"Level 18: Realise theres no way to finish this game, add 3 levels explaining your situation and submit", True, (255, 0, 0)),
                textpos = (0, 300)
                )

                            
levellist = [level0, level1, level2, level3, level4, level5, level6, level7, level8, level9, level10, level11, level12, level13, level14, level15, level16, level17]