#version 300 es
precision mediump float;
uniform sampler2D Texture;

out vec3 color;
in vec2 v_text;

void main() {

        color = texture(Texture,v_text).rgb;

        float fv = fract(v_text.y * float(textureSize(Texture,0).y));
        fv=min(1.0, 0.8+0.5*min(fv, 1.0-fv));
        color.rgb*=fv;


}
