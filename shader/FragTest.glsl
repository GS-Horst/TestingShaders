#version 300 es
//#version 460
precision mediump float;

uniform float iTime;
uniform vec2 u_resolution;
uniform vec2 u_mouse;

void main() {

	gl_FragColor = vec4(abs(sin(iTime)),0.0,1.0,1.0);
	//vec2 st = gl_FragCoord.xy/u_resolution;
	//gl_FragColor = vec4(st.x,st.y, 0.0, 1.0);	//Yellow (1.0, 1.0, 0.0, 1.0)	Top Right corner fo the screen
}