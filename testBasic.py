import pygame
import pgzero, pgzrun
import struct
import moderngl
from pygame.locals import *

WIDTH = 300
HEIGHT = 300

########### GAME LOGIC ###############
alien = Actor('alien')
alien.topright = 0, 10

def update():
    alien.left += 2
    if alien.left > WIDTH:
        alien.right = 0

def draw():
    VIRTUAL_RES=(300, 300)

    schirm = screen.surface.convert((255, 65280, 16711680, 0))
    pygame.display.set_mode((VIRTUAL_RES), DOUBLEBUF|OPENGL)
    ctx = moderngl.create_context()
    
    texture_coordinates = [0, 1,  1, 1,  0, 0,  1, 0]

    world_coordinates = [-1, -1,  1, -1,  -1,  1,  1,  1]

    render_indices = [0, 1, 2, 1, 2, 3]

    prog = ctx.program(
        vertex_shader = open("shader/VertexShader.glsl").read(),
        fragment_shader = open("shader/FragTest.glsl").read())

    screen_texture = ctx.texture(
        VIRTUAL_RES, 3,
        pygame.image.tostring(schirm, "RGB", 1))

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

    ###### RENDER ######

    texture_data = schirm.get_view('1')
    screen_texture.write(texture_data)
    ctx.clear(14/255,40/255,66/255)
    screen_texture.use()
    vao.render()

    ###########
    prog["u_time"] = 3.3
    ###########


    screen.clear()
    alien.draw()
######################################



###########
pgzrun.go()
