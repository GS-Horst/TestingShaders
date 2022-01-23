
import pgzero, pgzrun, pygame, sys, moderngl, struct
from random import *
from pygame.locals import *
from enum import Enum

WIDTH = 480 
HEIGHT = 800
TITLE = "Infinite Bunner - Lite"
ROW_HEIGHT = 40

class MyActor(Actor):
    def __init__(self, image, pos, anchor=("center", "bottom")):
        super().__init__(image, pos, anchor)

        self.children = []

    def draw(self, offset_x, offset_y):
        self.x += offset_x
        self.y += offset_y

        super().draw()
        for child_obj in self.children:
            child_obj.draw(self.x, self.y)

        self.x -= offset_x
        self.y -= offset_y

    def update(self):
        for child_obj in self.children:
            child_obj.update()

class PlayerState(Enum):
    ALIVE = 0
    SPLAT = 1
    SPLASH = 2
    EAGLE = 3

DIRECTION_UP = 0
DIRECTION_RIGHT = 1
DIRECTION_DOWN = 2
DIRECTION_LEFT = 3
direction_keys = [keys.UP, keys.RIGHT, keys.DOWN, keys.LEFT]

# X and Y directions indexed into by in_edge and out_edge in Segment
# The indices correspond to the direction numbers above, i.e. 0 = up, 1 = right, 2 = down, 3 = left
# Numbers 0 to 3 correspond to up, right, down, left
DX = [0,4,0,-4]
DY = [-4,0,4,0]

class Bunner(MyActor):
    MOVE_DISTANCE = 10

    def __init__(self, pos):
        super().__init__("blank", pos)

        self.state = PlayerState.ALIVE

        self.direction = 2
        self.timer = 0
        self.input_queue = []

        # Keeps track of the furthest distance we've reached so far in the level, for scoring
        # (Level Y coordinates decrease as the screen scrolls)
        self.min_y = self.y

    def handle_input(self, dir):
        for row in game.rows:
            if row.y == self.y + Bunner.MOVE_DISTANCE * DY[dir]:

                if row.allow_movement(self.x + Bunner.MOVE_DISTANCE * DX[dir]):

                    self.direction = dir
                    self.timer = Bunner.MOVE_DISTANCE

                return

    def update(self):
        for direction in range(4):
            if key_just_pressed(direction_keys[direction]):
                self.input_queue.append(direction)

        if self.state == PlayerState.ALIVE:
            # While the player is alive, the timer variable is used for movement. If it's zero, the player is on
            # the ground. If it's above zero, they're currently jumping to a new location.
            # Are we on the ground, and are there inputs to process?
            if self.timer == 0 and len(self.input_queue) > 0:
                # Take the next input off the queue and process it
                self.handle_input(self.input_queue.pop(0))

            land = False
            if self.timer > 0:
                # Apply movement
                self.x += DX[self.direction]
                self.y += DY[self.direction]
                self.timer -= 1
                land = self.timer == 0      # If timer reaches zero, we've just landed

            current_row = None
            for row in game.rows:
                if row.y == self.y:
                    current_row = row
                    break

            if current_row:
                # Row.check receives the player's X coordinate and returns the new state the player should be in
                # (normally ALIVE, but SPLAT or SPLASH if they've collided with a vehicle or if they've fallen in
                # the water). It also returns a second result which is only used if there was a collision, and even
                # then only for certain collisions. When the new state is SPLAT, we will add a new child object to the
                # current row, with the appropriate 'splat' image. In this case, the second result returned from
                # check_collision is a Y offset which affects the position of this new child object. If the player is
                # hit by a car the Y offset is zero.
                self.state, dead_obj_y_offset = current_row.check_collision(self.x)
                if self.state == PlayerState.ALIVE:
                    self.x += current_row.push()

                else:
                    if self.state == PlayerState.SPLAT:
                        current_row.children.insert(0, MyActor("splat" + str(self.direction), (self.x, dead_obj_y_offset)))
                    self.timer = 100
            else:
                if self.y > game.scroll_pos + HEIGHT + 80:
                    self.state = PlayerState.EAGLE
                    self.timer = 15

            self.x = max(16, min(WIDTH - 16, self.x))
        else:
            # Not alive - timer now counts down prior to game over screen
            self.timer -= 1

        # Keep track of the furthest we've got in the level
        self.min_y = min(self.min_y, self.y)

        # Choose sprite image
        self.image = "blank"
        if self.state == PlayerState.ALIVE:
            if self.timer > 0:
                self.image = "jump" + str(self.direction)
            else:
                self.image = "sit" + str(self.direction)
        elif self.state == PlayerState.SPLASH and self.timer > 84:
            self.image = "splash" + str(int((100 - self.timer) / 2))

# Mover is the base class for Car and Log
class Mover(MyActor):
    def __init__(self, dx, image, pos):
        super().__init__(image, pos)

        self.dx = dx

    def update(self):
        self.x += self.dx

class Car(Mover):


    def __init__(self, dx, pos):
        image = "car" + str(randint(0, 3)) + ("0" if dx < 0 else "1")
        super().__init__(dx, image, pos)

class Log(Mover):
    def __init__(self, dx, pos):
        image = "log" + str(randint(0, 1))
        super().__init__(dx, image, pos)

# Row is the base class for Grass, Dirt and ActiveRow
class Row(MyActor):
    def __init__(self, base_image, index, y):
        # base_image and index form the name of the image file to use # Last argument is the anchor point to use
        super().__init__(base_image + str(index), (0, y), ("left", "bottom"))

        self.index = index

        # X direction of moving elements on this row
        self.dx = 0

    def next(self):
        return

    def collide(self, x, margin=0):
        for child_obj in self.children:
            if x >= child_obj.x - (child_obj.width / 2) - margin and x < child_obj.x + (child_obj.width / 2) + margin:
                return child_obj

        return None

    def push(self):
        return 0

    def check_collision(self, x):
        return PlayerState.ALIVE, 0

    def allow_movement(self, x):
        return x >= 16 and x <= WIDTH-16

class ActiveRow(Row):
    def __init__(self, child_type, dxs, base_image, index, y):
        super().__init__(base_image, index, y)

        self.child_type = child_type    # Class to be used for child objects (e.g. Car)
        self.timer = 0
        self.dx = choice(dxs)   # Randomly choose a direction for cars/logs to move

        # Populate the row with child objects (cars or logs). Without this, the row would initially be empty.
        x = -WIDTH / 2 - 70
        while x < WIDTH / 2 + 70:
            x += randint(240, 480)
            pos = (WIDTH / 2 + (x if self.dx > 0 else -x), 0)
            self.children.append(self.child_type(self.dx, pos))

    def update(self):
        super().update()

        # Recreate the children list, excluding any which are too far off the edge of the screen to be visible
        self.children = [c for c in self.children if c.x > -70 and c.x < WIDTH + 70]

        self.timer -= 1

        # Create new child objects on a random interval
        if self.timer < 0:
            pos = (WIDTH + 70 if self.dx < 0 else -70, 0)
            self.children.append(self.child_type(self.dx, pos))
            # 240 is minimum distance between the start of one child object and the start of the next, assuming its
            self.timer = (1 + random()) * (240 / abs(self.dx))

class Grass(Row):
    def __init__(self, predecessor, index, y):
        super().__init__("grass", index, y)

    def next(self):
        if self.index <= 5:
            row_class, index = Grass, self.index + 8
        elif self.index == 6:
            row_class, index = Grass, 7
        elif self.index == 7:
            row_class, index = Grass, 15
        elif self.index >= 8 and self.index <= 14:
            row_class, index = Grass, self.index + 1
        else:
            row_class, index = choice((Road, Water)), 0

        # Create an object of the chosen row class
        return row_class(self, index, self.y - ROW_HEIGHT)

class Dirt(Row):
    def __init__(self, predecessor, index, y):
        super().__init__("dirt", index, y)

    def next(self):
        if self.index <= 5:
            row_class, index = Dirt, self.index + 8
        elif self.index == 6:
            row_class, index = Dirt, 7
        elif self.index == 7:
            row_class, index = Dirt, 15
        elif self.index >= 8 and self.index <= 14:
            row_class, index = Dirt, self.index + 1
        else:
            row_class, index = choice((Road, Water)), 0

        # Create an object of the chosen row class
        return row_class(self, index, self.y - ROW_HEIGHT)
    
class Water(ActiveRow):
    def __init__(self, predecessor, index, y):
        dxs = [-2,-1]*(predecessor.dx >= 0) + [1,2]*(predecessor.dx <= 0)
        super().__init__(Log, dxs, "water", index, y)

    def update(self):
        super().update()

        for log in self.children:
            # Child (log) object positions are relative to the parent row. If the player exists, and the player is at the
            # same Y position, and is colliding with the current log, make the log dip down into the water slightly

            ### Can be removed? ^^^
            if game.bunner and self.y == game.bunner.y and log == self.collide(game.bunner.x, -4):
                log.y = 2
            else:
                log.y = 0

    def push(self):
        return self.dx

    def check_collision(self, x):
        # If we're colliding with a log, that's a good thing!
        if self.collide(x, -4):
            return PlayerState.ALIVE, 0
        else:
            return PlayerState.SPLASH, 0

    def next(self):
        if self.index == 7 or (self.index >= 1 and random() < 0.5):
            row_class, index = Dirt, randint(4,6)
        else:
            row_class, index = Water, self.index + 1

        # Create an object of the chosen row class
        return row_class(self, index, self.y - ROW_HEIGHT)

class Road(ActiveRow):
    def __init__(self, predecessor, index, y):
        dxs = list(set(range(-5, 6)) - set([0, predecessor.dx]))
        super().__init__(Car, dxs, "road", index, y)

    def update(self):
        super().update()

    def check_collision(self, x):
        if self.collide(x):
            return PlayerState.SPLAT, 0
        else:
            return PlayerState.ALIVE, 0

    def next(self):
        if self.index == 0:
            row_class, index = Road, 1
        elif self.index < 5:
            r = random()
            if r < 0.8:
                row_class, index = Road, self.index + 1
            else:
                row_class, index = Grass, randint(0,6)
        else:
                row_class, index = Grass, randint(0,6)

        # Create an object of the chosen row class
        return row_class(self, index, self.y - ROW_HEIGHT)

class Game:
    def __init__(self, bunner=None):
        self.bunner = bunner
 
        self.eagle = None
        self.frame = 0

        # First (bottom) row is always grass
        self.rows = [Grass(None, 0, 0)]

        self.scroll_pos = -HEIGHT

    def update(self):
        if self.bunner:
            # Scroll faster if the player is close to the top of the screen. Limit scroll speed to
            # between 1 and 3 pixels per frame.
            ### Remove
            self.scroll_pos -= max(1, min(3, float(self.scroll_pos + HEIGHT - self.bunner.y) / (HEIGHT // 4)))
        else:
            self.scroll_pos -= 1

        # Recreate the list of rows, excluding any which have scrolled off the bottom of the screen
        self.rows = [row for row in self.rows if row.y < int(self.scroll_pos) + HEIGHT + ROW_HEIGHT * 2]

        while self.rows[-1].y > int(self.scroll_pos)+ROW_HEIGHT:
            new_row = self.rows[-1].next()
            self.rows.append(new_row)

        # Update all rows, and the player and eagle (if present)
        for obj in self.rows + [self.bunner, self.eagle]:
            if obj:
                obj.update()


        return self

    def draw(self):
        all_objs = list(self.rows)

        if self.bunner:
            all_objs.append(self.bunner)

        def sort_key(obj):
            # Adding 39 and then doing an integer divide by 40 (the height of each row) deals with the situation where
            # the player sprite would otherwise be drawn underneath the row below. 
            return (obj.y + 39) // ROW_HEIGHT
        all_objs.sort(key=sort_key)

        for obj in all_objs:
            if obj:
                # Draw the object, taking the scroll position into account
                obj.draw(0, -int(self.scroll_pos))

    def score(self):
        return int(-320 - game.bunner.min_y) // 40

key_status = {}

def key_just_pressed(key):
    result = False

    prev_status = key_status.get(key, False)

    if not prev_status and keyboard[key]:
        result = True

    key_status[key] = keyboard[key]

    return result

def display_number(n, colour, x, align):
    # align: 0 for left, 1 for right
    n = str(n)  # Convert number to string
    for i in range(len(n)):
        screen.blit("digit" + str(colour) + n[i], (x + (i - len(n) * align) * 25, 0))

# Pygame Zero calls the update and draw functions each frame

class State(Enum):
    MENU = 1
    PLAY = 2
    GAME_OVER = 3

def update():
    global state, game, high_score

    if state == State.MENU:
        if key_just_pressed(keys.SPACE):
            state = State.PLAY
            game = Game(Bunner((240, -320)))
        else:
            game.update()

    elif state == State.PLAY:
        # Is it game over?
        if game.bunner.state != PlayerState.ALIVE and game.bunner.timer < 0:
            state = State.GAME_OVER
        else:
            game.update()

    elif state == State.GAME_OVER:
        # Switch to menu state, and create a new game object without a player
        if key_just_pressed(keys.SPACE):

            state = State.MENU
            game = Game()

def draw(): ######## called by pgzrun.go()
    ######
    texture_data = screen.get_view('1')
    screen_texture.write(texture_data)
    ctx.clear(14/255,40/255,66/255)
    screen_texture.use()
    vao.draw()
    ######

    game.draw()

    if state == State.MENU:
        screen.blit("title", (0, 0))
        screen.blit("start" + str([0, 1, 2, 1][game.scroll_pos // 6 % 4]), ((WIDTH - 270) // 2, HEIGHT - 240))

    elif state == State.GAME_OVER:
        screen.blit("gameover", (0, 0))

# Set the initial game state
state = State.MENU

############
# ModernGL #
############
## Rendering according to Blubberquark's Blogpost ##

VIRTUAL_RES = (480, 800)
REAL_RES = (480, 800)

screen = pygame.Surface(VIRTUAL_RES).convert((255, 65280, 16711680, 0))
pygame.display.set_mode(REAL_RES, DOUBLEBUF|OPENGL)

ctx = moderngl.create_context()

texture_coordinates = [0, 1,  1, 1,  0, 0,  1, 0]

world_coordinates = [-1, -1,  1, -1,  -1,  1,  1,  1]

render_indices = [0, 1, 2, 1, 2, 3]

prog = ctx.program(
    vertex_shader = open("shader/VertexShader.glsl").read(),
    fragment_shader = open("shader/FragmentShader.glsl").read())

screen_texture = ctx.texture(
    VIRTUAL_RES, 3,
    pygame.image.tostring(screen, "RGB", 1))

screen_texture.repeat_x = False
screen_texture.repeat_y = False

vbo = ctx.buffer(struct.pack('8f', *world_coordinates))
uvmap = ctx.buffer(struct.pack('8f', *texture_coordinates))
ibo= ctx.buffer(struct.pack('6I', *render_indices))

vao_content = [
    (vbo, '2f', 'vert'),
    (uvmap, '2f', 'in_text')
]

vao = ctx.vertex_array(prog, vao_content, ibo)

################################
# Create a new Game object, without a Player object
game = Game()

pgzrun.go()
