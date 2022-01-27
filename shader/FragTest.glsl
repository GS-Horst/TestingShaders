#version 330
//precision mediump float;

uniform float u_time;
out vec4 fragColor;

void main() {

	fragColor = vec4(abs(sin(u_time)),0.0,1.0,1.0);

}
